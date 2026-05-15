"""Thin HTTP wrapper around the FastAPI backend.
All Streamlit pages call these helpers instead of using httpx directly.
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get(path: str):
    r = httpx.get(f"{BACKEND_URL}{path}", timeout=60.0)
    r.raise_for_status()
    return r.json()


def post(path: str, payload: dict):
    r = httpx.post(f"{BACKEND_URL}{path}", json=payload, timeout=120.0)
    r.raise_for_status()
    return r.json()


def delete(path: str):
    r = httpx.delete(f"{BACKEND_URL}{path}", timeout=30.0)
    r.raise_for_status()
    return r.json()


def put(path: str, payload: dict):
    r = httpx.put(f"{BACKEND_URL}{path}", json=payload, timeout=30.0)
    r.raise_for_status()
    return r.json()
