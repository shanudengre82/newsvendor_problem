# Mathematical Model

## Classic Newsvendor Problem

The newsvendor orders a quantity Q of newspapers at wholesale cost c_w and sells them at retail price p. Unsold papers have salvage value s. Each day:

- If demand D < Q: profit = p·D + s·(Q - D) - c_w·Q
- If demand D ≥ Q: profit = p·Q - c_w·Q (lost sales)

The optimal order Q* minimises expected cost and is given by the **critical ratio**:

```
Q* = F^{-1}(  (p - c_w) / (p - s)  )
```

where F is the CDF of demand and the ratio is the **service level**.

## Our Variant: Margin + Streak-Based Dissatisfaction

We simplify and extend the classic model:

### Setup

- **Decision variable**: margin M (units above forecast)
- **Inventory**: I = μ + M (fixed daily, where μ is mean demand)
- **Demand**: D_t ~ N(μ, σ), clipped at 0, integer
- **Costs**: c_under (per-unit cost of shortage), c_over (per-unit cost of overstock)

### Per-Day Loss

Given inventory I and demand D on day t:

1. **Shortfall**: s_t = max(0, D_t - I)
2. **Excess**: e_t = max(0, I - D_t)
3. **Streak**: n_t = number of consecutive days (including today) with shortfall > 0

**Key innovation**: Stockout loss scales with streak to reflect customer dissatisfaction:

```
stockout_loss_t = n_t × s_t × c_under
overstock_loss_t = e_t × c_over
total_loss_t = stockout_loss_t + overstock_loss_t
```

### Streak Logic

- If s_t > 0 (shortfall today): n_t = n_{t-1} + 1
- If s_t = 0 (no shortfall): n_t = 0

This captures the **compounding effect** of repeated stockouts on customer dissatisfaction and loyalty.

### Total Loss Over T Days

```
L(M) = Σ_{t=1}^{T} total_loss_t
```

### Optimisation

Find the margin M* that minimises expected total loss:

```
M* = argmin_M E[ L(M) ]
```

**Note**: No closed-form solution exists due to the streak term. Solution is found empirically via Monte Carlo sweep.

## Common Random Numbers (CRN)

To get a smooth optimisation curve, we use **common random numbers**:

1. Generate demand series D = [D_1, D_2, ..., D_T] with fixed seed.
2. For each margin M in a sweep:
   - Simulate with inventory I = μ + M.
   - Use the **same** D across all M.
3. Compute total loss L(M) for each M.

**Benefit**: Differences in loss are due purely to the margin choice, not randomness. The curve is smooth and the argmin is stable.

## Example: Three-Day Simulation

Demand: [12, 12, 12, 5]
Inventory: 10
c_under: $1.00
c_over: $0.50

| Day | D | I | s | e | n | L_stockout | L_overstock | L_total |
|-----|---|---|----|----|----|-----------|-------------|---------|
| 0   | 12 | 10 | 2 | 0 | 1 | 1×2×1 = 2 | 0 | 2 |
| 1   | 12 | 10 | 2 | 0 | 2 | 2×2×1 = 4 | 0 | 4 |
| 2   | 12 | 10 | 2 | 0 | 3 | 3×2×1 = 6 | 0 | 6 |
| 3   | 5  | 10 | 0 | 5 | 0 | 0 | 5×0.5 = 2.5 | 2.5 |
|     |    |    |    |    |    |          | **Total: 14.5** |

Note the escalating stockout loss (2, 4, 6) due to the streak multiplier.

## Interpretation

- **High c_under** (expensive shortage): Prefer higher margins.
- **High c_over** (expensive overstock): Prefer lower margins.
- **High σ** (high demand volatility): Prefer higher margins to buffer variance.
- **Streak effect**: Pushes optimal margin **upward** compared to classical newsvendor, because repeated stockouts are especially costly.
