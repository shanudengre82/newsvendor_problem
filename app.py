"""Streamlit app for visualizing the newsvendor problem."""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
import io
from newsvendor.model import simulate_demand, simulate, inventory_from_margin
from newsvendor.sweep import sweep_margins, best_margin, recommend
from newsvendor.data import load_daily_csv, DataFormatError, template_csv


# Page config
st.set_page_config(
    page_title="Newsvendor Problem Visualiser",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📰 Newsvendor Problem Visualiser")
st.markdown(
    """
    Learn how to optimise inventory margins in the **New York newsvendor problem**.
    Discover how margin (safety buffer) affects stockouts, customer dissatisfaction,
    and total loss.
    """
)

# ============================================================================
# Sidebar: Data source selection
# ============================================================================
st.sidebar.header("📁 Data Source")
data_source = st.sidebar.radio("Choose data source:", ["Simulated", "Import CSV"])

history = None
future = None
mode = "units"

if data_source == "Simulated":
    # Simulated mode
    st.sidebar.header("📊 Simulation Parameters")

    mu = st.sidebar.slider("Mean demand (μ)", min_value=10, max_value=200, value=50, step=5)
    sigma = st.sidebar.slider(
        "Demand std dev (σ)", min_value=1, max_value=50, value=10, step=1
    )
    days = st.sidebar.slider("Days to simulate", min_value=50, max_value=365, value=100, step=10)
    seed = st.sidebar.number_input("Random seed", value=42, step=1)

    # Generate demand
    demand = simulate_demand(mu=mu, sigma=sigma, days=days, seed=seed)
    baseline = np.full(days, mu)

else:  # Import CSV
    st.sidebar.header("📤 Upload Data")

    # Download template button
    template_text = template_csv()
    st.sidebar.download_button(
        label="📋 Download CSV Template",
        data=template_text,
        file_name="newsvendor_template.csv",
        mime="text/csv",
        help="Download a template to see the required format"
    )

    # File uploader
    uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            history, future = load_daily_csv(uploaded_file)
            demand = history["actual"].values.astype(int)
            baseline = history["forecast"].values

            st.sidebar.success(f"✓ Loaded {len(history)} history + {len(future)} future rows")

            # Mode selector for real data
            mode = st.sidebar.radio("Margin unit:", ["units", "percent"],
                                   format_func=lambda x: "Units (forecast + m)" if x == "units" else "Percent (forecast × (1 + m%))")
        except DataFormatError as e:
            st.sidebar.error(f"❌ Invalid CSV format:\n\n{str(e)}")
            st.stop()
    else:
        st.sidebar.info("Upload a CSV to get started.")
        st.stop()

# ============================================================================
# Sidebar: Costs and margin
# ============================================================================
st.sidebar.divider()
st.sidebar.header("💰 Costs")

c_under = st.sidebar.number_input(
    "Stockout cost per unit (c_under)", min_value=0.1, max_value=10.0, value=1.0, step=0.1
)
c_over = st.sidebar.number_input(
    "Overstock cost per unit (c_over)", min_value=0.1, max_value=10.0, value=0.5, step=0.1
)

st.sidebar.divider()
st.sidebar.header("📈 Margin Selection")

# Adjust slider range based on mode
if mode == "units":
    margin_max = 100
    margin_default = 10
    margin_label = "Current margin (units)"
else:
    margin_max = 50
    margin_default = 10
    margin_label = "Current margin (%)"

margin = st.sidebar.slider(
    margin_label, min_value=0, max_value=margin_max, value=margin_default, step=1
)

# ============================================================================
# Compute single-margin simulation
# ============================================================================
inventory = inventory_from_margin(baseline, margin, mode=mode)
sim_result = simulate(demand=demand, inventory=inventory, c_under=c_under, c_over=c_over)

# ============================================================================
# Tabs
# ============================================================================
tab1, tab2 = st.tabs(["📊 One Margin", "🎯 Find Best Margin"])

with tab1:
    st.header("Single Margin Analysis")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Total Loss",
            f"${sim_result['total_loss'].sum():.2f}",
            help="Sum of stockout and overstock losses"
        )
    with col2:
        st.metric(
            "Stockout Loss",
            f"${sim_result['stockout_loss'].sum():.2f}",
            help="Loss from stockouts, with streak multiplier"
        )
    with col3:
        st.metric(
            "Overstock Loss",
            f"${sim_result['overstock_loss'].sum():.2f}",
            help="Loss from unsold inventory"
        )
    with col4:
        st.metric(
            "Stockout Rate",
            f"{100 * sim_result['stockout'].mean():.1f}%",
            help="% of days with at least one stockout"
        )

    st.divider()

    # Chart 1: Demand vs Inventory over time
    fig1 = go.Figure()

    fig1.add_trace(go.Scatter(
        x=np.arange(len(sim_result)),
        y=sim_result["demand"],
        mode="lines",
        name="Demand",
        line=dict(color="steelblue", width=2)
    ))

    # Add inventory line(s) - handle scalar or array
    if isinstance(inventory, (int, float)):
        fig1.add_hline(y=inventory, line_dash="dash", line_color="green", name="Inventory level")
    else:
        fig1.add_trace(go.Scatter(
            x=np.arange(len(sim_result)),
            y=inventory,
            mode="lines",
            name="Inventory level",
            line=dict(color="green", width=2, dash="dash")
        ))

    # Highlight stockout days
    stockout_days = sim_result[sim_result["stockout"]].index
    if len(stockout_days) > 0:
        fig1.add_trace(go.Scatter(
            x=stockout_days,
            y=sim_result.loc[stockout_days, "demand"],
            mode="markers",
            marker=dict(size=8, color="red"),
            name="Stockout days",
            showlegend=True
        ))

    fig1.update_layout(
        title="Demand vs Inventory Over Time (Stockout Days Highlighted)",
        xaxis_title="Day",
        yaxis_title="Units",
        hovermode="x unified",
        height=400
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Streak duration
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=np.arange(len(sim_result)),
        y=sim_result["streak"],
        name="Consecutive stockout days",
        marker_color="orange"
    ))
    fig2.update_layout(
        title="Stockout Streak Duration (Customer Dissatisfaction Multiplier)",
        xaxis_title="Day",
        yaxis_title="Streak Day (n)",
        height=350,
        hovermode="x unified"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: Loss breakdown by day
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=np.arange(len(sim_result)),
        y=sim_result["overstock_loss"],
        name="Overstock loss",
        marker_color="lightblue"
    ))
    fig3.add_trace(go.Bar(
        x=np.arange(len(sim_result)),
        y=sim_result["stockout_loss"],
        name="Stockout loss (streak-adjusted)",
        marker_color="salmon"
    ))
    fig3.update_layout(
        title="Daily Loss Breakdown (Stacked)",
        xaxis_title="Day",
        yaxis_title="Loss ($)",
        barmode="stack",
        height=350,
        hovermode="x unified"
    )
    st.plotly_chart(fig3, use_container_width=True)

with tab2:
    st.header("Margin Optimisation")
    st.write(
        "Sweep through a range of margins to find the inventory level that minimises "
        "total loss (overstock + stockout with customer dissatisfaction)."
    )

    # Sweep parameters
    col1, col2 = st.columns(2)
    with col1:
        if mode == "units":
            max_margin = st.slider("Max margin to sweep", min_value=10, max_value=100, value=50, step=5)
        else:
            max_margin = st.slider("Max margin to sweep (%)", min_value=5, max_value=50, value=25, step=5)
    with col2:
        margin_step = st.slider("Margin step size", min_value=1, max_value=10, value=2, step=1)

    # Run sweep
    margins_to_sweep = list(range(0, max_margin + 1, margin_step))
    with st.spinner("Computing margin sweep..."):
        sweep_result = sweep_margins(
            demand=demand,
            mu=baseline,
            margins=margins_to_sweep,
            c_under=c_under,
            c_over=c_over,
            mode=mode
        )

    # Best margin
    best_idx = best_margin(sweep_result)
    best_margin_value = sweep_result.loc[best_idx, "margin"]
    best_loss = sweep_result.loc[best_idx, "total_loss"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Best margin (this sweep)",
            f"{best_margin_value} {'units' if mode == 'units' else '%'}",
            help="Inventory = forecast + margin" if mode == "units" else "Inventory = forecast × (1 + margin%)"
        )
    with col2:
        st.metric(
            "Minimum total loss",
            f"${best_loss:.2f}",
            help="Total loss at optimal margin"
        )

    # Warn if on boundary
    if best_margin_value == margins_to_sweep[0] or best_margin_value == margins_to_sweep[-1]:
        st.warning(f"⚠️ Best margin is at the sweep boundary ({best_margin_value}). Consider widening the range.")

    st.divider()

    # Chart 1: Total loss vs margin
    fig1 = go.Figure()

    fig1.add_trace(go.Scatter(
        x=sweep_result["margin"],
        y=sweep_result["overstock_loss"],
        fill="tozeroy",
        name="Overstock loss",
        line=dict(color="lightblue"),
        fillcolor="rgba(135, 206, 235, 0.3)"
    ))

    fig1.add_trace(go.Scatter(
        x=sweep_result["margin"],
        y=sweep_result["overstock_loss"] + sweep_result["stockout_loss"],
        fill="tonexty",
        name="Stockout loss",
        line=dict(color="salmon"),
        fillcolor="rgba(250, 128, 114, 0.3)"
    ))

    # Mark best margin
    fig1.add_vline(
        x=best_margin_value,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Best: {best_margin_value}",
        annotation_position="top right"
    )

    # Mark current margin
    fig1.add_vline(
        x=margin,
        line_dash="dot",
        line_color="purple",
        annotation_text=f"Current: {margin}",
        annotation_position="top left"
    )

    fig1.update_layout(
        title="Total Loss vs Margin (Stacked: Overstock + Stockout)",
        xaxis_title=f"Margin ({'units' if mode == 'units' else '%'})",
        yaxis_title="Total Loss ($)",
        hovermode="x unified",
        height=400
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Stockout rate vs margin
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=sweep_result["margin"],
        y=sweep_result["stockout_rate"] * 100,
        mode="lines+markers",
        name="Stockout rate",
        line=dict(color="red", width=3)
    ))
    fig2.update_layout(
        title="Stockout Rate vs Margin",
        xaxis_title=f"Margin ({'units' if mode == 'units' else '%'})",
        yaxis_title="Stockout rate (%)",
        hovermode="x unified",
        height=350
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: Max streak vs margin
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=sweep_result["margin"],
        y=sweep_result["max_streak"],
        mode="lines+markers",
        name="Max streak",
        line=dict(color="orange", width=3)
    ))
    fig3.update_layout(
        title="Maximum Consecutive Stockout Days vs Margin",
        xaxis_title=f"Margin ({'units' if mode == 'units' else '%'})",
        yaxis_title="Max streak (days)",
        hovermode="x unified",
        height=350
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Recommended inventory section (only for imported data with future rows)
    if data_source == "Import CSV" and future is not None and len(future) > 0:
        st.divider()
        st.header("📋 Recommended Inventory")
        st.write(f"Using the best margin ({best_margin_value}), here are the recommended stock levels for future days:")

        future_copy = future.copy()
        rec_df = recommend(future_copy, baseline_col="forecast", margin=best_margin_value, mode=mode)

        # Display as table
        st.dataframe(rec_df, use_container_width=True)

        # Chart: Forecast vs Recommended
        fig_rec = go.Figure()
        fig_rec.add_trace(go.Scatter(
            x=rec_df["date"],
            y=rec_df["forecast"],
            mode="lines+markers",
            name="Forecast",
            line=dict(color="blue")
        ))
        fig_rec.add_trace(go.Scatter(
            x=rec_df["date"],
            y=rec_df["recommended_stock"],
            mode="lines+markers",
            name="Recommended stock",
            line=dict(color="green")
        ))
        fig_rec.update_layout(
            title="Forecast vs Recommended Stock (Future Days)",
            xaxis_title="Date",
            yaxis_title="Units",
            hovermode="x unified",
            height=350
        )
        st.plotly_chart(fig_rec, use_container_width=True)

        # Download CSV
        csv_buffer = io.StringIO()
        rec_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        st.download_button(
            label="📥 Download Recommended Stock (CSV)",
            data=csv_data,
            file_name="newsvendor_recommendations.csv",
            mime="text/csv"
        )

st.sidebar.divider()
st.sidebar.markdown(
    """
    **How to use this app:**

    **Simulated Mode:**
    1. Adjust demand distribution parameters (μ, σ).
    2. Use the **One Margin** tab to see the impact.
    3. Use **Find Best Margin** to optimise.

    **Import CSV Mode:**
    1. Download the template and prepare your data.
    2. Upload a CSV with columns: date, actual, forecast.
    3. Blank 'actual' values mark future days.
    4. Get best margin and future recommendations.

    **Key Insight:**
    Stockout loss multiplies with consecutive days (customer dissatisfaction),
    so repeated stockouts are much more costly than isolated ones.
    """
)
