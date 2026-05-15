"""Streamlit Dashboard — main entry page."""
from datetime import date
import streamlit as st
from api_client import get, post, put, delete

# Load base currency once per render
try:
    _settings = get("/settings")
    BASE_CURRENCY = _settings["base_currency"]
    BASE_SYMBOL = _settings["symbol"]
    SUPPORTED_CURRENCIES = _settings["supported_currencies"]
except Exception:
    BASE_CURRENCY = "INR"
    BASE_SYMBOL = "₹"
    SUPPORTED_CURRENCIES = [{"code": "INR", "symbol": "₹", "name": "Indian Rupee"}]

CURRENCY_CODES = [c["code"] for c in SUPPORTED_CURRENCIES]
CURRENCY_LABELS = [f"{c['symbol']} {c['code']}" for c in SUPPORTED_CURRENCIES]

st.set_page_config(page_title="AI Expense Tracker", page_icon="💰", layout="wide")

st.title("💰 AI Expense Tracker")
st.caption(
    f"Powered by Llama on Groq • Base currency: **{BASE_SYMBOL} {BASE_CURRENCY}** "
    f"(change in Settings) • Use the sidebar to navigate"
)

# ============================ Salary ============================
st.subheader("💼 Salary")
col_sal_a, col_sal_b = st.columns([2, 1])

with col_sal_a:
    try:
        salary_data = get("/salary")
        if "total_salary" in salary_data:
            st.metric("This Month's Salary",
                      f"{BASE_SYMBOL}{salary_data['total_salary']:,.0f}")
        else:
            st.info("No salary recorded for this month yet.")
    except Exception as e:
        st.error(f"Could not load salary: {e}")

with col_sal_b:
    sal_tab1, sal_tab2 = st.tabs(["✏️ Set / Edit", "➕ Add to existing"])

    _sal_idx = CURRENCY_CODES.index(BASE_CURRENCY) if BASE_CURRENCY in CURRENCY_CODES else 0

    # ----- Tab 1: SET (replace) -----
    with sal_tab1:
        st.caption("Replaces the salary with the value below (converted to base currency).")
        with st.form("salary_set_form", clear_on_submit=True):
            sub_a, sub_b = st.columns([2, 1])
            with sub_a:
                set_amt = st.number_input(
                    "Set salary to", min_value=0.0, step=100.0,
                    key="set_salary_amt",
                )
            with sub_b:
                set_curr_label = st.selectbox(
                    "Currency", CURRENCY_LABELS, index=_sal_idx,
                    key="set_salary_curr",
                )
            set_curr = CURRENCY_CODES[CURRENCY_LABELS.index(set_curr_label)]

            if st.form_submit_button("💾 Save"):
                result = put("/salary", {"amount": set_amt, "currency": set_curr})
                if result.get("original_currency"):
                    st.success(
                        f"Set salary: {result['original_currency']} {result['original_amount']:,.2f} → "
                        f"{BASE_SYMBOL}{result['total_salary']:,.2f} (rate {result['exchange_rate']})"
                    )
                st.rerun()

    # ----- Tab 2: ADD to existing -----
    with sal_tab2:
        st.caption(
            "Adds the amount below to your current salary. Great for bonuses, "
            "side income, or salary in a different currency."
        )
        with st.form("salary_add_form", clear_on_submit=True):
            sub_c, sub_d = st.columns([2, 1])
            with sub_c:
                add_amt = st.number_input(
                    "Amount to add", min_value=0.0, step=100.0,
                    key="add_salary_amt",
                )
            with sub_d:
                add_curr_label = st.selectbox(
                    "Currency", CURRENCY_LABELS, index=_sal_idx,
                    key="add_salary_curr",
                )
            add_curr = CURRENCY_CODES[CURRENCY_LABELS.index(add_curr_label)]

            if st.form_submit_button("➕ Add"):
                result = post("/salary", {"amount": add_amt, "currency": add_curr})
                if result.get("original_currency"):
                    st.success(
                        f"Added: {result['original_currency']} {result['original_amount']:,.2f} → "
                        f"{BASE_SYMBOL}{result['added_amount']:,.2f} "
                        f"(rate {result['exchange_rate']}). "
                        f"New total: {BASE_SYMBOL}{result['total_salary']:,.2f}"
                    )
                else:
                    st.success(f"New total salary: {BASE_SYMBOL}{result['total_salary']:,.2f}")
                st.rerun()

# ============================ Savings ============================
st.subheader("📈 This Month at a Glance")
try:
    savings = get("/savings")
    if "summary" in savings:
        c1, c2, c3 = st.columns(3)
        c1.metric("Salary", f"{BASE_SYMBOL}{savings['summary']['salary']:,.0f}")
        c2.metric("Spent", f"{BASE_SYMBOL}{savings['summary']['total_expenses']:,.0f}")
        c3.metric("Savings", f"{BASE_SYMBOL}{savings['summary']['savings']:,.0f}")
        st.caption(savings.get("status", ""))
    else:
        st.info(savings.get("message", "Add salary to see savings."))
except Exception as e:
    st.error(f"Could not load savings: {e}")

st.divider()

# ============================ Add Expense ============================
st.subheader("➕ Add an Expense")

tab_nl, tab_manual = st.tabs([
    "🪄 Natural Language (AI)",
    "Manual Add",
])

# -------- Natural Language Tab --------
with tab_nl:
    st.caption(
        "Type a full sentence — AI extracts title, amount, AND category. "
        "Example: _\"I spent 1000 rs on food at zomato\"_"
    )
    with st.form("nl_form", clear_on_submit=True):
        nl_text = st.text_input(
            "Describe the expense in one line",
            placeholder='e.g. "Paid 350 for uber to office"',
        )
        nl_col1, nl_col2 = st.columns([1, 1])
        with nl_col1:
            nl_date = st.date_input("Date", value=date.today(), key="nl_date")
        with nl_col2:
            _idx = CURRENCY_CODES.index(BASE_CURRENCY) if BASE_CURRENCY in CURRENCY_CODES else 0
            nl_curr_label = st.selectbox(
                "Currency typed in", CURRENCY_LABELS,
                index=_idx, key="nl_curr",
                help="Will be converted to your base currency if different.",
            )
        nl_currency = CURRENCY_CODES[CURRENCY_LABELS.index(nl_curr_label)]

        if st.form_submit_button("Parse & Add with AI"):
            if nl_text.strip():
                with st.spinner("🤖 AI is parsing your sentence..."):
                    try:
                        result = post("/expenses/natural", {
                            "text": nl_text,
                            "date": nl_date.isoformat(),
                            "currency": nl_currency,
                        })
                        exp = result["expense"]
                        msg = (f"Added **{exp['title']}** • {BASE_SYMBOL}{exp['amount']:,.2f} • "
                               f"**{exp['category']}** • {exp['date']}")
                        if "original_currency" in exp and exp["original_currency"] != BASE_CURRENCY:
                            msg += (f" _(from {exp['original_currency']} "
                                    f"{exp['original_amount']:,.2f} @ rate {exp['exchange_rate']})_")
                        st.success(msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not parse: {e}")

# -------- Manual Add Tab --------
with tab_manual:
    with st.form("manual_form", clear_on_submit=True):
        m_title = st.text_input("Title", key="manual_title")
        m_col_a, m_col_b = st.columns([2, 1])
        with m_col_a:
            m_amount = st.number_input("Amount", min_value=0.0, step=50.0,
                                       key="manual_amount")
        with m_col_b:
            _idx_m = CURRENCY_CODES.index(BASE_CURRENCY) if BASE_CURRENCY in CURRENCY_CODES else 0
            m_curr_label = st.selectbox(
                "Currency", CURRENCY_LABELS, index=_idx_m, key="manual_curr",
            )
        m_currency = CURRENCY_CODES[CURRENCY_LABELS.index(m_curr_label)]
        m_category = st.selectbox("Category", [
            "Food", "Transport", "Shopping", "Bills",
            "Entertainment", "Health", "Education", "Miscellaneous"
        ])
        m_date = st.date_input("Date", value=date.today(), key="manual_date")
        if st.form_submit_button("Add"):
            result = post("/expenses", {
                "title": m_title,
                "amount": m_amount,
                "category": m_category,
                "currency": m_currency,
                "date": m_date.isoformat(),
            })
            exp = result.get("expense", {})
            if "original_currency" in exp and exp["original_currency"] != BASE_CURRENCY:
                st.success(
                    f"Converted {exp['original_currency']} {exp['original_amount']:,.2f} → "
                    f"{BASE_SYMBOL}{exp['amount']:,.2f} (rate {exp['exchange_rate']})"
                )
            st.rerun()

st.divider()

# ============================ Recent Expenses ============================
st.subheader("📋 This Month's Expenses")

# Track which expense is currently being edited
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

CATEGORIES = ["Food", "Transport", "Shopping", "Bills",
              "Entertainment", "Health", "Education", "Miscellaneous"]

try:
    data = get("/expenses")
    if "expenses" in data and data["expenses"]:
        st.caption(f"Showing {data['total_count']} expense(s)")
        for expense in data["expenses"]:
            is_editing = st.session_state.editing_id == expense["id"]

            # ----- Row layout: title | amount | category | edit | delete -----
            cols = st.columns([3, 1, 2, 0.6, 0.6])
            cols[0].write(f"**{expense['title']}**")
            cols[1].write(f"{BASE_SYMBOL}{expense['amount']:,.0f}")
            cols[2].write(f"_{expense['category']}_")

            if cols[3].button("✏️", key=f"edit_{expense['id']}",
                              help="Edit this expense"):
                st.session_state.editing_id = (
                    None if is_editing else expense["id"]
                )
                st.rerun()

            if cols[4].button("🗑", key=f"del_{expense['id']}",
                              help="Delete this expense"):
                delete(f"/expenses/{expense['id']}")
                if is_editing:
                    st.session_state.editing_id = None
                st.rerun()

            # ----- Inline edit form (shown when this row is being edited) -----
            if is_editing:
                with st.container(border=True):
                    st.markdown("**✏️ Editing expense**")
                    with st.form(f"edit_form_{expense['id']}",
                                 clear_on_submit=False):
                        new_title = st.text_input(
                            "Title", value=expense["title"],
                            key=f"e_title_{expense['id']}",
                        )
                        new_amount = st.number_input(
                            f"Amount ({BASE_SYMBOL})",
                            value=float(expense["amount"]),
                            min_value=0.0, step=50.0,
                            key=f"e_amt_{expense['id']}",
                        )
                        current_cat = expense.get("category", "Miscellaneous")
                        if current_cat not in CATEGORIES:
                            current_cat = "Miscellaneous"
                        new_category = st.selectbox(
                            "Category", CATEGORIES,
                            index=CATEGORIES.index(current_cat),
                            key=f"e_cat_{expense['id']}",
                        )

                        save_col, cancel_col = st.columns([1, 1])
                        save_clicked = save_col.form_submit_button(
                            "💾 Save", use_container_width=True
                        )
                        cancel_clicked = cancel_col.form_submit_button(
                            "❌ Cancel", use_container_width=True
                        )

                        if save_clicked:
                            put(f"/expenses/{expense['id']}", {
                                "title": new_title,
                                "amount": new_amount,
                                "category": new_category,
                            })
                            st.session_state.editing_id = None
                            st.rerun()
                        elif cancel_clicked:
                            st.session_state.editing_id = None
                            st.rerun()
    else:
        st.info("No expenses recorded this month yet. Add one above! 👆")
except Exception as e:
    st.error(f"Could not load expenses: {e}")
