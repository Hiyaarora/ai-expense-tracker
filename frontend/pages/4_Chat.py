"""Chat page — conversational AI with tool use over your expenses."""
import streamlit as st
from api_client import post

st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")
st.title("💬 Chat with Your Expenses")
st.caption("Powered by GPT-OSS-120B on Groq with Tool Use / Function Calling")

with st.expander("💡 What can I ask?", expanded=False):
    st.markdown(
        """
        **Read questions:**
        - How much have I spent this month?
        - How much on food / shopping / transport?
        - What's my salary?
        - Am I saving well? How much is left?

        **Modify your data:**
        - Add ₹150 for coffee
        - Add a 500 rupee Zomato order
        - Delete the coffee expense
        - Change my Uber expense to 400

        The AI will figure out which database operation to perform and reply naturally.
        """
    )

# ===================== Session state =====================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar reset button
with st.sidebar:
    if st.button("🔄 Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()

# ===================== Render history =====================
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===================== Chat input =====================
user_input = st.chat_input("Ask me anything about your expenses...")

if user_input:
    # Show user message immediately
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = post("/chat", {
                    "message": user_input,
                    "history": st.session_state.chat_history[:-1],
                })
                reply = response.get("reply", "Sorry, no reply.")
            except Exception as e:
                reply = f"⚠️ Error: {e}"
        st.markdown(reply)

    st.session_state.chat_history.append({"role": "assistant", "content": reply})
