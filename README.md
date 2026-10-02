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

### Local (without Docker)

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

### Docker Compose

Run the entire app in a container:

```bash
docker compose up --build
```

The app will be available at http://localhost:8501. Press Ctrl+C to stop.

**Additional Docker commands:**

```bash
# Stop and clean up
docker compose down

# Run tests in a container
docker compose run --rm tests

# View logs
docker compose logs -f app

# Expose the app on your network (edit docker-compose.yml and change ports)
# From: "127.0.0.1:8501:8501"
# To:   "0.0.0.0:8501:8501"
# Then run: docker compose up --build
```

If exposing on the network, restrict access via a firewall or reverse proxy.

## Data Format

The app supports two modes:

### Simulated Mode
- Generate synthetic demand from a normal distribution
- Adjust mean (μ), std dev (σ), days, and random seed
- Useful for exploration and teaching

### Import CSV Mode
- Upload real historical and forecast data
- **Required format**: CSV with columns `date, actual, forecast` (lowercase, in that order)
- **date**: ISO `YYYY-MM-DD`, sorted ascending, daily frequency, no gaps or duplicates
- **actual**: Non-negative number or blank. Blank values mark the future window (forecast-only)
- **forecast**: Non-negative number, required on every row
- **Minimum requirement**: At least 30 historical rows (with an `actual` value)

**Example CSV:**
```
date,actual,forecast
2026-01-01,10,12
2026-01-02,11,13
2026-01-03,12,14
2026-01-04,,15
2026-01-05,,16
```
- Rows 1–3: History (training data)
- Rows 4–5: Future (forecast-only, for recommendations)

The app will validate your CSV and show clear error messages if the format is incorrect.

## Running Tests

```bash
python -m pytest tests/ -v
```

Or use the convenience script:

```bash
./run_tests.sh
```

## Project Structure

- `newsvendor/model.py` — Core simulation: demand generation, per-day inventory, streak loss calculation
- `newsvendor/data.py` — CSV loading and validation (daily format only)
- `newsvendor/sweep.py` — Margin sweep, best-margin optimisation, future recommendations
- `app.py` — Streamlit UI: simulated and import modes, margin units vs percent
- `sample_data/sample_daily.csv` — Example data (120 days history + 14 days future)
- `newsvendor/overview.py` — Historical vs forecast visualization (simulated and real data modes)
- `tests/` — 59 tests covering all modules (TDD)

## How It Works

### Demand Model

**Forecast (Expected Demand):**
A seasonal sinusoidal pattern represents expected demand with weekly cycles:
```
expected_t = μ · (1 + a·sin(2πt/7))
```
where `a` is the seasonality amplitude (0–50% of μ, default 20%).

**Actual Demand:**
Daily demand is generated with forecast error (noise):
```
demand_t = expected_t + noise ~ N(0, σ), clipped at 0, rounded to integers
```

**Forecast Line:**
The forecast shown in plots is the rounded expected demand:
```
forecast_t = round(expected_t)
```

### Inventory & Loss

Each day:
1. `inventory = forecast + margin` (or `forecast × (1 + margin%)` in percent mode)
2. `shortfall = max(0, demand - inventory)`
3. `excess = max(0, inventory - demand)`
4. Update streak: if `shortfall > 0`, increment; else reset to 0.
5. **Stockout loss** = `streak × shortfall × c_under` (streak multiplier captures dissatisfaction)
6. **Overstock loss** = `excess × c_over`
7. **Total loss** = stockout + overstock loss

**Stockout and Waste Rules:**
- **Stockout** occurs only when `actual > stock` (forecast below actual demand)
- **Waste** (excess inventory) occurs when `stock > actual` (forecast above actual demand)

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
- **Seasonality** in the forecast allows realistic patterns where demand varies predictably (e.g., weekly cycles).
- **Forecast accuracy** is paramount: if forecast is consistently below actual, stockouts dominate; if consistently above, waste dominates.
- **Historical vs forecast visualization** shows stockout days (red markers) and waste areas (green shading), making the margin's impact visible.

## Interpretation

Use the app to:
1. Understand how demand variability (σ) affects optimal margins.
2. Adjust the seasonality slider to model realistic demand patterns (e.g., weekly variation).
3. See the trade-off between underage cost (c_under) and overage cost (c_over).
4. Visualise in Plot 1 how stockouts (red 'x' markers) and waste (green shading) vary with margin.
5. Use Plot 2 (Find Best Margin) to find the margin that minimises total loss given your costs and demand distribution.
6. Experiment with different cost ratios to find realistic optima.

## Licence

This project is licenced under the MIT Licence. See [LICENSE](LICENSE) for details.
