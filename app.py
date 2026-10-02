"""Streamlit app for visualizing the newsvendor problem."""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
from newsvendor.model import simulate_demand, simulate
from newsvendor.sweep import sweep_margins, best_margin


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
# Sidebar: parameters
# ============================================================================
st.sidebar.header("📊 Simulation Parameters")

mu = st.sidebar.slider("Mean demand (μ)", min_value=10, max_value=200, value=50, step=5)
sigma = st.sidebar.slider(
    "Demand std dev (σ)", min_value=1, max_value=50, value=10, step=1
)
days = st.sidebar.slider("Days to simulate", min_value=50, max_value=365, value=100, step=10)
seed = st.sidebar.number_input("Random seed", value=42, step=1)

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

margin = st.sidebar.slider(
    "Current margin (units)", min_value=0, max_value=100, value=10, step=1
)

# ============================================================================
# Generate demand and simulate
# ============================================================================
demand = simulate_demand(mu=mu, sigma=sigma, days=days, seed=seed)
inventory = mu + margin

# ============================================================================
# Tabs
# ============================================================================
tab1, tab2 = st.tabs(["📊 One Margin", "🎯 Find Best Margin"])

with tab1:
    st.header("Single Margin Analysis")

    # Run simulation
    sim_result = simulate(demand=demand, inventory=inventory, c_under=c_under, c_over=c_over)

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

    fig1.add_hline(y=inventory, line_dash="dash", line_color="green", name="Inventory level")

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
        max_margin = st.slider("Max margin to sweep", min_value=10, max_value=100, value=50, step=5)
    with col2:
        margin_step = st.slider("Margin step size", min_value=1, max_value=10, value=2, step=1)

    # Run sweep
    margins_to_sweep = list(range(0, max_margin + 1, margin_step))
    with st.spinner("Computing margin sweep..."):
        sweep_result = sweep_margins(
            demand=demand,
            mu=mu,
            margins=margins_to_sweep,
            c_under=c_under,
            c_over=c_over
        )

    # Best margin
    best_idx = best_margin(sweep_result)
    best_margin_value = sweep_result.loc[best_idx, "margin"]
    best_loss = sweep_result.loc[best_idx, "total_loss"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Best margin (this sweep)",
            f"{best_margin_value} units",
            help="Inventory = mean demand + margin"
        )
    with col2:
        st.metric(
            "Minimum total loss",
            f"${best_loss:.2f}",
            help="Total loss at optimal margin"
        )

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
        xaxis_title="Margin (units)",
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
        xaxis_title="Margin (units)",
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
        xaxis_title="Margin (units)",
        yaxis_title="Max streak (days)",
        hovermode="x unified",
        height=350
    )
    st.plotly_chart(fig3, use_container_width=True)

st.sidebar.divider()
st.sidebar.markdown(
    """
    **How to use this app:**

    1. Adjust simulation parameters in the sidebar.
    2. Use the **One Margin** tab to see the impact of a single margin choice.
    3. Use the **Find Best Margin** tab to optimise across many margins.
    4. The stockout loss multiplier increases with consecutive stockout days,
       reflecting customer dissatisfaction.
    """
)
