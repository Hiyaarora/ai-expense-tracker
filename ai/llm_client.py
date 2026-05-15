"""LLM client wrapper (Groq + Llama 3.3 70B).
All AI calls go through this module so the provider can be swapped later
by changing only this file.
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv

from ai.prompts import (
    INSIGHTS_PROMPT,
    ADVICE_PROMPT,
    CATEGORIZE_PROMPT,
    CHAT_SYSTEM_PROMPT,
)
from ai.tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()

MODEL_NAME = "openai/gpt-oss-120b"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _ask_groq(system: str, user_message: str, max_tokens: int = 800) -> str:
    """Single-turn text generation."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def generate_monthly_insights(summary_data: dict, salary):
    """Plain-English paragraph summarizing the month's spending."""
    user_msg = json.dumps({
        "month": summary_data.get("month"),
        "total_spent": summary_data.get("total"),
        "category_breakdown": summary_data.get("summary"),
        "salary": salary,
        "currency": summary_data.get("currency", "INR"),
    }, indent=2)
    return _ask_groq(INSIGHTS_PROMPT, user_msg, max_tokens=400)


def generate_budget_advice(summary_data: dict, salary):
    """Three personalized saving tips as a numbered list."""
    user_msg = json.dumps({
        "month": summary_data.get("month"),
        "total_spent": summary_data.get("total"),
        "category_breakdown": summary_data.get("summary"),
        "salary": salary,
    }, indent=2)
    return _ask_groq(ADVICE_PROMPT, user_msg, max_tokens=500)


def categorize_expense(title: str) -> str:
    """Pick a category for the given expense title."""
    valid = {"Food", "Transport", "Shopping", "Bills",
             "Entertainment", "Health", "Education", "Miscellaneous"}
    raw = _ask_groq(CATEGORIZE_PROMPT, title, max_tokens=20)
    cleaned = raw.split("\n")[0].strip().strip(".").strip()
    return cleaned if cleaned in valid else "Miscellaneous"


def chat_with_tools(user_message: str, history: list) -> str:
    """Multi-turn chat with manual tool-call loop.

    history: list of {"role": "user"|"assistant", "content": "..."} dicts.
    Returns the final assistant text after Groq calls any needed tools.
    """
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for msg in history or []:
        if msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    # Tool-call loop (max 8 iterations to prevent runaway)
    for _ in range(8):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            max_tokens=1024,
        )

        choice = response.choices[0]
        msg = choice.message

        # If no tool calls, we have the final answer
        if not msg.tool_calls:
            return (msg.content or "").strip()

        # Otherwise, append assistant message + execute each tool call
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name,
                                 "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                fn_args = {}

            if fn_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[fn_name](**fn_args)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"Unknown tool: {fn_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": fn_name,
                "content": json.dumps(result, default=str),
            })

    return "Sorry, I couldn't complete that request — please try rephrasing."
