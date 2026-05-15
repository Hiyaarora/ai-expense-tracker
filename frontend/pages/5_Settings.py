"""Settings page — pick your base currency."""
import streamlit as st
from api_client import get, put

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")

try:
    data = get("/settings")
except Exception as e:
    st.error(f"Could not load settings: {e}")
    st.stop()

current_base = data["base_currency"]
current_symbol = data["symbol"]
supported = data["supported_currencies"]

st.subheader("💱 Base Currency")
st.caption(
    "All your expenses are stored and displayed in this currency. "
    "If you add an expense in a different currency, it will be converted "
    "at the current exchange rate (via frankfurter.dev)."
)

col_a, col_b = st.columns([1, 2])
with col_a:
    st.metric("Current Base Currency", f"{current_symbol} {current_base}")

with col_b:
    options = [f"{c['symbol']} {c['code']} — {c['name']}" for c in supported]
    codes = [c["code"] for c in supported]
    current_idx = codes.index(current_base) if current_base in codes else 0

    new_choice = st.selectbox(
        "Change base currency",
        options,
        index=current_idx,
        key="base_curr_selector",
    )
    new_code = codes[options.index(new_choice)]

    if new_code != current_base:
        if st.button(f"Set base currency to {new_code}",
                     type="primary", use_container_width=True):
            result = put("/settings", {"base_currency": new_code})
            st.success(f"✅ {result['message']}")
            st.rerun()
    else:
        st.info("Pick a different currency above to change it.")

st.divider()

with st.expander("ℹ️ How currency conversion works"):
    st.markdown(
        """
        - **You** can type expenses in ANY supported currency (USD, EUR, GBP, etc.)
        - **The system** converts to your base currency using live exchange rates
        - **Stored data** is always in base currency, so totals and charts are accurate
        - **Original amount** + exchange rate are also stored for transparency
        - Rates are cached for 1 hour to avoid hammering the free API

        Powered by [frankfurter.dev](https://frankfurter.dev) — a free, no-key
        exchange rate API.
        """
    )

st.divider()
st.subheader("Supported Currencies")
cols = st.columns(4)
for i, c in enumerate(supported):
    with cols[i % 4]:
        st.write(f"**{c['symbol']} {c['code']}** — {c['name']}")
