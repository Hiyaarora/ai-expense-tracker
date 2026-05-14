from fastapi import FastAPI
from routes import expenses, salary

app = FastAPI(title="Expense Tracker API")

# Plug in routes
app.include_router(expenses.router)
app.include_router(salary.router)

@app.get("/")
async def read_root():
    return {"message": "Expense Tracker API is running!"}