# Demo 01 - Basic sandwich detection

## What this shows

`swaps.json` is a small, chronological DEX swap history for a single
USDC/WETH constant-product pool across two blocks.

- **Block 1000** contains a classic **sandwich**:
  1. `0xfront` - attacker buys WETH with 5,000 USDC (front-run) at index 0.
     The swap records the pre-attack pool reserves
     (`reserve_in=2,000,000 USDC`, `reserve_out=1,000 WETH`).
  2. `0xvictim` - an unrelated trader buys WETH with 10,000 USDC (index 1).
     Because the attacker already pushed the price up, the victim receives
     fewer WETH than they would have on the untouched pool.
  3. `0xback` - the attacker sells their WETH back for USDC (back-run, index 2),
     pocketing the difference.
- **Block 1001** contains two ordinary, unrelated swaps that must **not** be
  flagged (different senders, no enclosing front/back pair).

## How to run

```
python -m mevscope scan demos/01-basic/swaps.json
python -m mevscope scan demos/01-basic/swaps.json --format json
python -m mevscope scan demos/01-basic/swaps.json --fail-on-mev   # exit 1
```

## Expected result

- **Exactly one** sandwich is detected (the block-1000 attack).
- Detection `method` is `exact` because pre-attack reserves are present, so the
  victim loss is the counterfactual constant-product (x*y=k) shortfall valued in
  USDC. The reported `victim_loss_in` is positive (the victim got materially
  fewer WETH than the untouched pool would have given for 10,000 USDC).
- The attacker's profit is positive and denominated in USDC.
- With `--fail-on-mev`, the CLI exits with code **1**.
- Total victim loss and total attacker profit are reported.
