"""Streamlit Dashboard — main entry page."""
import streamlit as st
from api_client import get, post, delete

st.set_page_config(page_title="AI Expense Tracker", page_icon="💰", layout="wide")

st.title("💰 AI Expense Tracker")
st.caption("Powered by Llama on Groq • Use the sidebar to navigate")

# ============================ Salary ============================
st.subheader("💼 Salary")
col_sal_a, col_sal_b = st.columns([2, 1])

with col_sal_a:
    try:
        salary_data = get("/salary")
        if "total_salary" in salary_data:
            st.metric("This Month's Salary",
                      f"₹{salary_data['total_salary']:,.0f}")
        else:
            st.info("No salary recorded for this month yet.")
    except Exception as e:
        st.error(f"Could not load salary: {e}")

with col_sal_b:
    with st.form("salary_form", clear_on_submit=True):
        sal_amt = st.number_input("Add to this month's salary",
                                  min_value=0.0, step=1000.0)
        if st.form_submit_button("Save"):
            post("/salary", {"amount": sal_amt, "currency": "INR"})
            st.rerun()

# ============================ Savings ============================
st.subheader("📈 This Month at a Glance")
try:
    savings = get("/savings")
    if "summary" in savings:
        c1, c2, c3 = st.columns(3)
        c1.metric("Salary", f"₹{savings['summary']['salary']:,.0f}")
        c2.metric("Spent", f"₹{savings['summary']['total_expenses']:,.0f}")
        c3.metric("Savings", f"₹{savings['summary']['savings']:,.0f}")
        st.caption(savings.get("status", ""))
    else:
        st.info(savings.get("message", "Add salary to see savings."))
except Exception as e:
    st.error(f"Could not load savings: {e}")

st.divider()

# ============================ Add Expense ============================
st.subheader("➕ Add an Expense")

tab1, tab2 = st.tabs(["✨ Smart Add (AI picks category)", "Manual Add"])

with tab1:
    st.caption("Just type the title and amount — Llama figures out the category.")
    with st.form("smart_form", clear_on_submit=True):
        s_title = st.text_input("What did you spend on?",
                                placeholder="e.g. Zomato dinner, Uber to airport")
        s_amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0,
                                   key="smart_amount")
        smart_submit = st.form_submit_button("Add with AI")
        if smart_submit and s_title and s_amount > 0:
            with st.spinner("🤖 AI is picking a category..."):
                result = post("/expenses/smart", {
                    "title": s_title,
                    "amount": s_amount,
                    "currency": "INR",
                })
            st.success(
                f"Added under **{result['expense']['category']}** category!"
            )
            st.rerun()

with tab2:
    with st.form("manual_form", clear_on_submit=True):
        m_title = st.text_input("Title", key="manual_title")
        m_amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0,
                                   key="manual_amount")
        m_category = st.selectbox("Category", [
            "Food", "Transport", "Shopping", "Bills",
            "Entertainment", "Health", "Education", "Miscellaneous"
        ])
        if st.form_submit_button("Add"):
            post("/expenses", {
                "title": m_title,
                "amount": m_amount,
                "category": m_category,
                "currency": "INR",
            })
            st.rerun()

st.divider()

# ============================ Recent Expenses ============================
st.subheader("📋 This Month's Expenses")
try:
    data = get("/expenses")
    if "expenses" in data and data["expenses"]:
        st.caption(f"Showing {data['total_count']} expense(s)")
        # Display with delete buttons
        for expense in data["expenses"]:
            cols = st.columns([3, 1, 2, 1])
            cols[0].write(f"**{expense['title']}**")
            cols[1].write(f"₹{expense['amount']:,.0f}")
            cols[2].write(f"_{expense['category']}_")
            if cols[3].button("🗑", key=f"del_{expense['id']}"):
                delete(f"/expenses/{expense['id']}")
                st.rerun()
    else:
        st.info("No expenses recorded this month yet. Add one above! 👆")
except Exception as e:
    st.error(f"Could not load expenses: {e}")
