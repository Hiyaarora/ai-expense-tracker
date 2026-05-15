"""AI Insights page — Llama analyzes your spending and gives advice."""
import streamlit as st
from api_client import get

st.set_page_config(page_title="AI Insights", page_icon="🤖", layout="wide")
st.title("🤖 AI Insights")
st.caption("Powered by GPT-OSS-120B on Groq • Analyzes your real spending data")

col1, col2 = st.columns(2)

# ===================== Monthly Insights =====================
with col1:
    st.subheader("📝 Monthly Summary")
    st.markdown(
        "AI reads your expense data and writes a plain-English paragraph "
        "summarizing your spending patterns this month."
    )
    if st.button("Generate Insights", key="insights_btn",
                 use_container_width=True):
        with st.spinner("🤖 AI is analyzing your spending..."):
            try:
                data = get("/insights/monthly")
                st.success("Analysis complete!")
                st.markdown(f"> {data.get('insights', 'No insights available.')}")
            except Exception as e:
                st.error(f"Error: {e}")

# ===================== Budget Advice =====================
with col2:
    st.subheader("💡 Budget Advice")
    st.markdown(
        "AI gives you 3 specific, personalized tips to save more based on "
        "your real spending — not generic advice."
    )
    if st.button("Get Saving Tips", key="advice_btn",
                 use_container_width=True):
        with st.spinner("🤖 AI is preparing personalized advice..."):
            try:
                data = get("/advice")
                st.success("Tips ready!")
                st.markdown(data.get("advice", "No advice available."))
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.caption(
    "💡 How this works: Your expense data is sent to an AI model along with a "
    "specific prompt. The model returns a natural-language response that's "
    "shown back to you here. No prebuilt rules — pure AI reasoning."
)
