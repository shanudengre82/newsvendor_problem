# Quick Start Guide

## 1. Install & Run

```bash
# Clone or navigate to the project
cd newsvendor_problem

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

The app opens at **http://localhost:8501**.

## 2. Explore the UI

### Sidebar Parameters

Adjust these in real-time to see their impact:

- **Mean demand (μ)**: 10–200 units/day
- **Demand std dev (σ)**: How unpredictable is demand?
- **Days to simulate**: 50–365 days
- **Stockout cost (c_under)**: How expensive is running out?
- **Overstock cost (c_over)**: How expensive is leftover stock?
- **Current margin**: The buffer units above mean demand

### Tab 1: One Margin

**See how one margin choice performs:**

1. Adjust the **Current margin** slider (sidebar).
2. Watch 4 charts update:
   - **Demand vs Inventory**: Line chart showing demand and your inventory level.
     - Red dots = days when you ran out.
   - **Stockout Streak Duration**: Bar chart showing consecutive stockout days (n = 1, 2, 3, ...).
   - **Daily Loss Breakdown**: Stacked bars of overstock loss (blue) + stockout loss (red).
3. **Summary metrics** show total loss, stockout rate, etc.

### Tab 2: Find Best Margin

**Discover the optimal margin:**

1. Adjust **Max margin to sweep** and **Step size** (default: 0–50 by 2s).
2. Click or wait for the sweep to compute (~1 second).
3. Explore 3 charts:
   - **Total Loss vs Margin** (main chart): Shows where the "sweet spot" is.
     - Stacked: overstock loss (light blue) + stockout loss (salmon).
     - Green dash: Best margin.
     - Purple dot: Current margin (from slider).
   - **Stockout Rate vs Margin**: Falls as margin rises (monotonic).
   - **Max Streak vs Margin**: Longest stockout streak decreases with margin.

## 3. Key Takeaways

**What to experiment with:**

- **Increase c_under** (high cost of running out) → Best margin shifts right (higher).
- **Increase c_over** (high cost of overstock) → Best margin shifts left (lower).
- **Increase σ** (high demand variability) → Best margin shifts right (buffer against volatility).
- **Increase μ** (overall demand level) → Best margin may shift based on cost ratio.

**The streak effect:**

- The **orange bars** in Tab 1 show how dissatisfaction multiplies (n = 1, 2, 3, ...).
- This is why repeated stockouts are much more costly than the classical newsvendor model predicts.
- The optimal margin is higher than pure cost-based logic would suggest.

## 4. Run Tests

```bash
# All 18 tests
pytest tests/ -v

# Or use the provided script
./run_tests.sh
```

Expected output:
```
59 passed in 0.42s ✓
```

## 5. Example Scenario

**You are a newsvendor for The New York Times:**

- Mean demand: **μ = 50** papers/day
- Demand variability: **σ = 10** (some days are busier)
- Wholesale cost: **$0.50** per paper
- Retail price: **$1.50** per paper
- Unsold salvage value: **$0.10** per paper

**Costs:**
- Stockout cost (lost profit + dissatisfaction): **c_under = $1.00** per paper short
- Overstock cost (disposal): **c_over = $0.40** per paper left

**Experiment:**
1. Set μ = 50, σ = 10, c_under = $1.00, c_over = $0.40, Seasonality = 20% (default).
2. Open Tab 2: Find Best Margin.
3. Sweep 0–30 margin by 1.
4. The algorithm finds that **margin = 6 units** minimizes total loss ($453.40).
5. This means you should stock about **56 papers** daily (forecast ≈ 50 + margin 6).

**Why not stock 50 (no margin)?**
- Too many stockout days → customer dissatisfaction compounds via the streak multiplier.
- Repeated stockouts destroy customer loyalty and cost far more than isolated ones.

**Why not stock 80 (huge margin)?**
- Too much leftover stock → overstock losses dominate (disposal cost).
- You're paying to hold and discard papers that won't sell.

**The balance is ~58–60.** The app shows exactly where your data lands.

## 6. Next Steps

- **Vary cost ratios** to see how profit margins affect inventory decisions.
- **Try different demand distributions** (currently normal; could be Poisson, lognormal, etc.).
- **Export results** for external analysis or decision-support systems.
- **Extend the model** with lead times, batch ordering, or time-series demand.

---

**Happy experimenting! 📊**
