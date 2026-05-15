"""Yearly Summary page — month-wise + category bars."""
import streamlit as st
import plotly.express as px
import pandas as pd
from api_client import get

st.set_page_config(page_title="Yearly Summary", page_icon="📈", layout="wide")
st.title("📈 Yearly Summary")

try:
    data = get("/expenses/summary/yearly")
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

# ============= Header metric =============
col_a, col_b = st.columns(2)
col_a.metric(
    f"Total Spent in {data['year']}",
    f"₹{data['grand_total']:,.0f}",
)
col_b.metric(
    "Categories Used",
    f"{len(data.get('category_totals', {}))}",
)

if data["grand_total"] == 0:
    st.info("No expenses recorded for this year yet.")
    st.stop()

st.divider()

# ============= Month-wise bar chart =============
st.subheader("Month-wise Spending")
monthly_df = pd.DataFrame([
    {"Month": m, "Amount": v}
    for m, v in data["monthly_totals"].items()
])

fig_bar = px.bar(
    monthly_df,
    x="Month",
    y="Amount",
    text="Amount",
    color="Amount",
    color_continuous_scale="Viridis",
)
fig_bar.update_traces(
    texttemplate="₹%{text:,.0f}",
    textposition="outside",
    hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>",
)
fig_bar.update_layout(showlegend=False, coloraxis_showscale=False,
                     yaxis_title="Amount (₹)", xaxis_title="")
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ============= Category totals YTD =============
st.subheader("Category Totals (Year-to-Date)")
if data.get("category_totals"):
    cat_df = pd.DataFrame(
        [{"Category": k, "Amount": v} for k, v in data["category_totals"].items()]
    ).sort_values("Amount", ascending=False)

    fig_cat = px.bar(
        cat_df,
        x="Category",
        y="Amount",
        text="Amount",
        color="Category",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig_cat.update_traces(
        texttemplate="₹%{text:,.0f}",
        textposition="outside",
        hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>",
    )
    fig_cat.update_layout(showlegend=False,
                         yaxis_title="Amount (₹)", xaxis_title="")
    st.plotly_chart(fig_cat, use_container_width=True)
