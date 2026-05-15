"""Monthly Summary page — category breakdown with pie chart."""
from datetime import datetime
import streamlit as st
import plotly.express as px
import pandas as pd
from api_client import get

st.set_page_config(page_title="Monthly Summary", page_icon="📊", layout="wide")
st.title("📊 Monthly Summary")

# Load base currency for display
try:
    _settings = get("/settings")
    SYMBOL = _settings["symbol"]
except Exception:
    SYMBOL = "₹"

# ============= Month / Year selector =============
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
current_year = datetime.now().year
current_month_name = datetime.now().strftime("%B")

filter_col1, filter_col2, _ = st.columns([1, 1, 3])
with filter_col1:
    selected_month = st.selectbox(
        "Month", MONTHS, index=MONTHS.index(current_month_name)
    )
with filter_col2:
    # Show 5 years back, plus current year, plus 1 year forward
    year_options = list(range(current_year - 4, current_year + 2))
    selected_year = st.selectbox(
        "Year", year_options, index=year_options.index(current_year)
    )

try:
    data = get(f"/expenses/summary/monthly?month={selected_month}&year={selected_year}")
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
    f"{SYMBOL}{data['total']:,.0f}",
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
                      hovertemplate=f"%{{label}}: {SYMBOL}%{{value:,.0f}}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Breakdown Table")
    df_display = df.copy()
    df_display["Percentage"] = (df_display["Amount"] / df_display["Amount"].sum() * 100).round(1)
    df_display["Amount"] = df_display["Amount"].apply(lambda x: f"{SYMBOL}{x:,.0f}")
    df_display["Percentage"] = df_display["Percentage"].apply(lambda x: f"{x}%")
    st.dataframe(df_display, hide_index=True, use_container_width=True)

    # Top category callout
    top_cat = df.iloc[0]
    pct = (top_cat["Amount"] / data["total"]) * 100
    st.info(
        f"🏆 Your biggest expense category is **{top_cat['Category']}** "
        f"at {SYMBOL}{top_cat['Amount']:,.0f} ({pct:.0f}%)"
    )
