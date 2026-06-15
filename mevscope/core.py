"""Core MEV detection engine.

Given a chronologically-ordered list of DEX swaps (one pool, blocks of trades),
this engine reconstructs the constant-product (x*y=k) pool state and detects
sandwich attacks: an attacker BUY immediately before a victim trade, followed by
an attacker SELL of the same token shortly after, within the same block.

Loss accounting: for the victim, we compute the price they actually received
versus the price they *would* have received if the attacker's front-run had not
moved the pool. The difference (in the input token) is the victim's loss.

No network calls. Pure replay over the supplied swap list.

Swap schema (per JSON record):
    {
      "tx":      "0x...",       # tx hash (str)
      "block":   12345,           # block number (int)
      "index":   3,               # intra-block log index (int) - ordering key
      "sender":  "0x...",       # EOA / router caller (str, lowercased)
      "pool":    "0x...",       # pool address (str)
      "token_in":  "USDC",      # symbol or address of token sold INTO pool
      "token_out": "WETH",      # symbol or address of token bought FROM pool
      "amount_in":  1000.0,       # human-readable amount in (float)
      "amount_out": 0.5,          # human-readable amount out (float)
      "reserve_in":  2000000.0,   # optional: pool reserve of token_in BEFORE swap
      "reserve_out": 1000.0       # optional: pool reserve of token_out BEFORE swap
    }

Reserves are optional; when present they enable precise counterfactual loss.
When absent, loss is estimated from the realized price gap between the victim
and the attacker's back-run (a conservative lower bound).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

# How close (in intra-block ordering) attacker legs must bracket the victim.
# Sandwiches are atomic within a block; we require same block and the victim
# sitting between the two attacker legs.


@dataclass
class Swap:
    tx: str
    block: int
    index: int
    sender: str
    pool: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    reserve_in: float | None = None
    reserve_out: float | None = None

    @property
    def price(self) -> float:
        """Execution price expressed as token_in per token_out (cost basis)."""
        if self.amount_out == 0:
            return float("inf")
        return self.amount_in / self.amount_out

    def pair_key(self) -> tuple[str, str, str]:
        """Direction-agnostic pool/token-pair key."""
        a, b = sorted([self.token_in.lower(), self.token_out.lower()])
        return (self.pool.lower(), a, b)


@dataclass
class Sandwich:
    pool: str
    attacker: str
    block: int
    frontrun_tx: str
    victim_tx: str
    backrun_tx: str
    victim_sender: str
    token_in: str
    token_out: str
    victim_amount_in: float
    victim_amount_out: float
    # Loss to the victim, denominated in the victim's token_in.
    victim_loss_in: float
    # Attacker realized profit, denominated in the token they cycled (token_out of frontrun).
    attacker_profit: float
    profit_token: str
    # "exact" (reserves known) or "estimated" (price-gap inference).
    method: str


@dataclass
class Report:
    swaps_analyzed: int
    sandwiches: list[Sandwich] = field(default_factory=list)

    @property
    def total_victim_loss(self) -> float:
        return sum(s.victim_loss_in for s in self.sandwiches)

    @property
    def total_attacker_profit(self) -> float:
        return sum(s.attacker_profit for s in self.sandwiches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "swaps_analyzed": self.swaps_analyzed,
            "sandwich_count": len(self.sandwiches),
            "total_victim_loss": round(self.total_victim_loss, 8),
            "total_attacker_profit": round(self.total_attacker_profit, 8),
            "sandwiches": [
                {k: (round(v, 8) if isinstance(v, float) else v) for k, v in asdict(s).items()}
                for s in self.sandwiches
            ],
        }


def load_swaps_from_obj(obj: Any) -> list[Swap]:
    """Build Swap objects from a parsed JSON object (list of records or {'swaps': [...]})."""
    if isinstance(obj, dict) and "swaps" in obj:
        obj = obj["swaps"]
    if not isinstance(obj, list):
        raise ValueError("expected a JSON array of swaps or an object with a 'swaps' array")
    swaps: list[Swap] = []
    for i, rec in enumerate(obj):
        if not isinstance(rec, dict):
            raise ValueError(f"swap #{i} is not an object")
        try:
            tx = str(rec["tx"])
            block = int(rec["block"])
            index = int(rec["index"])
            sender = str(rec["sender"]).lower()
            pool = str(rec["pool"]).lower()
            token_in = str(rec["token_in"])
            token_out = str(rec["token_out"])
            amount_in = float(rec["amount_in"])
            amount_out = float(rec["amount_out"])
            reserve_in = (float(rec["reserve_in"]) if rec.get("reserve_in") is not None else None)
            reserve_out = (float(rec["reserve_out"]) if rec.get("reserve_out") is not None else None)
        except KeyError as e:
            raise ValueError(f"swap #{i} missing required field {e}") from None
        except (TypeError, ValueError) as e:
            raise ValueError(f"swap #{i} has invalid field value: {e}") from None

        if block < 0:
            raise ValueError(f"swap #{i} has negative block number: {block}")
        if index < 0:
            raise ValueError(f"swap #{i} has negative index: {index}")
        if amount_in < 0:
            raise ValueError(f"swap #{i} has negative amount_in: {amount_in}")
        if amount_out < 0:
            raise ValueError(f"swap #{i} has negative amount_out: {amount_out}")
        if not tx.strip():
            raise ValueError(f"swap #{i} has empty tx hash")
        if not token_in.strip():
            raise ValueError(f"swap #{i} has empty token_in")
        if not token_out.strip():
            raise ValueError(f"swap #{i} has empty token_out")
        if reserve_in is not None and reserve_in < 0:
            raise ValueError(f"swap #{i} has negative reserve_in: {reserve_in}")
        if reserve_out is not None and reserve_out < 0:
            raise ValueError(f"swap #{i} has negative reserve_out: {reserve_out}")

        swaps.append(
            Swap(
                tx=tx,
                block=block,
                index=index,
                sender=sender,
                pool=pool,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=amount_out,
                reserve_in=reserve_in,
                reserve_out=reserve_out,
            )
        )
    return swaps


def load_swaps(path: str) -> list[Swap]:
    """Load swaps from a JSON file path."""
    with open(path, "r", encoding="utf-8") as fh:
        return load_swaps_from_obj(json.load(fh))


def _amount_out_cpmm(amount_in: float, reserve_in: float, reserve_out: float) -> float:
    """Constant-product (Uniswap v2) output for a given input, ignoring fees.

    out = reserve_out - k / (reserve_in + amount_in), k = reserve_in * reserve_out
    """
    k = reserve_in * reserve_out
    new_reserve_in = reserve_in + amount_in
    if new_reserve_in <= 0:
        return 0.0
    new_reserve_out = k / new_reserve_in
    return reserve_out - new_reserve_out


def _exact_victim_loss(front: Swap, victim: Swap) -> float | None:
    """Counterfactual loss using known pre-front-run reserves.

    The victim trades token_in -> token_out. With the front-run present, the
    pool reserves the victim faces are shifted. We reconstruct the reserves the
    victim WOULD have faced without the front-run (i.e. the reserves recorded on
    the front-run swap, which are the pre-front-run state) and compute the output
    they would have received for the same amount_in. The loss is the input-token
    value of the missing output, priced at the victim's realized execution price.
    """
    if front.reserve_in is None or front.reserve_out is None:
        return None
    # Front-run is in the same direction as the victim (attacker buys token_out).
    # Pre-front-run reserves are those recorded on the front-run.
    r_in = front.reserve_in
    r_out = front.reserve_out
    if r_in <= 0 or r_out <= 0:
        return None
    ideal_out = _amount_out_cpmm(victim.amount_in, r_in, r_out)
    missing_out = ideal_out - victim.amount_out
    if missing_out <= 0:
        return 0.0
    # Value the missing output in token_in at the victim's realized price.
    return missing_out * victim.price


def _estimated_victim_loss(front: Swap, victim: Swap, back: Swap) -> float:
    """Lower-bound loss when reserves are unknown.

    The attacker's back-run sells token_out back for token_in at a better price
    than the victim received (that gap is the extracted value). We estimate the
    victim's loss as the output shortfall implied by the price the back-run got
    versus the price the victim got, applied to the victim's output size.
    """
    # back-run direction is reversed: token_in/out swapped relative to victim.
    # back.price is token_out-per-token_in in victim terms; invert to compare.
    if back.amount_in == 0 or victim.amount_out == 0:
        return 0.0
    # Price the victim paid (token_in per token_out).
    victim_px = victim.price
    # Price implied by the back-run, expressed in the same token_in-per-token_out units.
    # back sells token_out -> token_in, so token_in-per-token_out = amount_out / amount_in.
    back_px = back.amount_out / back.amount_in if back.amount_in else victim_px
    gap = victim_px - back_px
    if gap <= 0:
        return 0.0
    return gap * victim.amount_out


def _attacker_profit(front: Swap, back: Swap) -> tuple[float, str]:
    """Attacker profit denominated in the token they started and ended with (token_in of front).

    Front: token_in -> token_out (spends X token_in, gets Q token_out).
    Back:  token_out -> token_in (spends Q' token_out, gets Y token_in).
    Profit = Y - X in token_in, when the attacker fully unwinds.
    """
    spent = front.amount_in
    received = back.amount_out
    return (received - spent, front.token_in)


def detect_sandwiches(swaps: Iterable[Swap]) -> list[Sandwich]:
    """Detect sandwich attacks across the supplied swaps.

    Algorithm:
      1. Group swaps by (pool, token-pair) and sort by (block, index).
      2. Within each group, slide over swaps. A sandwich is:
           front (attacker, dir A->B) ... victim (other sender, dir A->B) ...
           back (same attacker, dir B->A), all in the SAME block, with the
           victim's index strictly between front and back.
      3. The nearest enclosing front/back pair owned by one attacker around a
         distinct victim is flagged.
    """
    by_group: dict[tuple[str, str, str], list[Swap]] = {}
    for s in swaps:
        by_group.setdefault(s.pair_key(), []).append(s)

    found: list[Sandwich] = []
    used_tx: set[str] = set()

    for group in by_group.values():
        group.sort(key=lambda s: (s.block, s.index))
        n = len(group)
        for i in range(n):
            front = group[i]
            if front.tx in used_tx:
                continue
            # Look for a back-run by the same attacker, opposite direction, same block.
            for j in range(i + 1, n):
                back = group[j]
                if back.block != front.block:
                    break  # groups sorted; later blocks won't match this front
                if back.tx in used_tx:
                    continue
                if back.sender != front.sender:
                    continue
                # opposite direction
                if not (back.token_in == front.token_out and back.token_out == front.token_in):
                    continue
                # Find a victim strictly between, same direction as front, different sender.
                victims = [
                    v for v in group[i + 1 : j]
                    if v.block == front.block
                    and v.sender != front.sender
                    and v.token_in == front.token_in
                    and v.token_out == front.token_out
                    and v.tx not in used_tx
                ]
                if not victims:
                    continue
                # Largest victim by amount_in is the principal sandwich target.
                victim = max(victims, key=lambda v: v.amount_in)

                exact = _exact_victim_loss(front, victim)
                if exact is not None:
                    loss, method = exact, "exact"
                else:
                    loss, method = _estimated_victim_loss(front, victim, back), "estimated"
                profit, profit_tok = _attacker_profit(front, back)

                found.append(
                    Sandwich(
                        pool=front.pool,
                        attacker=front.sender,
                        block=front.block,
                        frontrun_tx=front.tx,
                        victim_tx=victim.tx,
                        backrun_tx=back.tx,
                        victim_sender=victim.sender,
                        token_in=victim.token_in,
                        token_out=victim.token_out,
                        victim_amount_in=victim.amount_in,
                        victim_amount_out=victim.amount_out,
                        victim_loss_in=loss,
                        attacker_profit=profit,
                        profit_token=profit_tok,
                        method=method,
                    )
                )
                used_tx.update({front.tx, victim.tx, back.tx})
                break  # this front consumed
    found.sort(key=lambda s: (s.block, s.victim_tx))
    return found


def build_report(swaps: list[Swap]) -> Report:
    return Report(swaps_analyzed=len(swaps), sandwiches=detect_sandwiches(swaps))
