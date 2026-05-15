"""Monthly Summary page — category breakdown with pie chart."""
import streamlit as st
import plotly.express as px
import pandas as pd
from api_client import get

st.set_page_config(page_title="Monthly Summary", page_icon="📊", layout="wide")
st.title("📊 Monthly Summary")

try:
    data = get("/expenses/summary/monthly")
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

if not data.get("summary"):
    st.info("No expenses recorded this month yet. Go to the Dashboard to add some.")
    st.stop()

# ============= Header metric =============
col_a, col_b = st.columns(2)
col_a.metric(
    f"Total Spent in {data['month']}",
    f"₹{data['total']:,.0f}",
    help=f"{data.get('expense_count', 0)} transactions",
)
col_b.metric(
    "Categories",
    f"{len(data['summary'])}",
)

st.divider()

# ============= Build dataframe =============
df = pd.DataFrame(
    [{"Category": k, "Amount": v} for k, v in data["summary"].items()]
).sort_values("Amount", ascending=False)

# ============= Two columns: chart + table =============
left, right = st.columns([1, 1])

with left:
    st.subheader("Spending by Category")
    fig = px.pie(
        df,
        names="Category",
        values="Amount",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_traces(textinfo="percent+label",
                      hovertemplate="%{label}: ₹%{value:,.0f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Breakdown Table")
    df_display = df.copy()
    df_display["Percentage"] = (df_display["Amount"] / df_display["Amount"].sum() * 100).round(1)
    df_display["Amount"] = df_display["Amount"].apply(lambda x: f"₹{x:,.0f}")
    df_display["Percentage"] = df_display["Percentage"].apply(lambda x: f"{x}%")
    st.dataframe(df_display, hide_index=True, use_container_width=True)

    # Top category callout
    top_cat = df.iloc[0]
    pct = (top_cat["Amount"] / data["total"]) * 100
    st.info(
        f"🏆 Your biggest expense category is **{top_cat['Category']}** "
        f"at ₹{top_cat['Amount']:,.0f} ({pct:.0f}%)"
    )
