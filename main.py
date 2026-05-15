from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import expenses, salary, ai

app = FastAPI(title="AI Expense Tracker API")

# Allow Streamlit frontend (or any browser) to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(expenses.router)
app.include_router(salary.router)
app.include_router(ai.router)


@app.get("/")
async def read_root():
    return {"message": "AI Expense Tracker API is running!"}
