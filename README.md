# Newsvendor Problem Visualiser

An interactive Streamlit app to visually understand the **New York newspaper vendor problem** — how to optimise inventory margins to minimise total loss (overstock + stockout with customer dissatisfaction).

## Features

- **Interactive Simulation**: Adjust demand distribution (μ, σ), costs, and margin in real-time.
- **Streak-Based Loss**: Stockout loss increases with consecutive stockout days, reflecting customer dissatisfaction.
- **Two Visualisation Tabs**:
  - **One Margin**: See the impact of a single margin choice over time.
  - **Find Best Margin**: Sweep across margins and find the optimal balance.
- **Common Random Numbers**: Use the same demand series across all margins for stable, smooth optimisation curves.

## Installation

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the App

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Running Tests

```bash
python -m pytest tests/ -v
```

Or use the convenience script:

```bash
./run_tests.sh
```

## Project Structure

- `newsvendor/model.py` — Core simulation: demand generation, inventory simulation with streak logic.
- `newsvendor/sweep.py` — Margin sweep and best-margin optimisation.
- `app.py` — Streamlit application with interactive visualisations.
- `tests/` — Test suite (TDD).

## How It Works

### Demand Model

Daily demand is generated from a normal distribution:
```
demand ~ N(μ, σ), clipped at 0, rounded to integers
```

### Inventory & Loss

Each day:
1. `inventory = mean_demand + margin`
2. `shortfall = max(0, demand - inventory)`
3. `excess = max(0, inventory - demand)`
4. Update streak: if `shortfall > 0`, increment; else reset to 0.
5. **Stockout loss** = `streak × shortfall × c_under` (streak multiplier captures dissatisfaction)
6. **Overstock loss** = `excess × c_over`
7. **Total loss** = stockout + overstock loss

### Margin Optimisation

Sweep across multiple margins using **common random numbers** (same demand series for all margins). This ensures:
- Smooth loss curves
- Stable, reliable optimisation
- One clear best margin with minimal noise

## Key Insights

- **Higher margins** reduce stockout rate and streaks, but increase overstock losses.
- **Lower margins** reduce overstock loss, but expose to many stockouts with escalating dissatisfaction.
- The **best margin** minimises total loss — found empirically by sweep (no closed-form solution due to streak term).
- **Customer dissatisfaction** (streak multiplier) is key: repeated stockouts are much more costly than isolated ones.

## Interpretation

Use the app to:
1. Understand how demand variability (σ) affects optimal margins.
2. See the trade-off between underage cost (c_under) and overage cost (c_over).
3. Visualise why **a buffer above forecast demand reduces losses**.
4. Experiment with different cost ratios to find realistic optima.
