from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Get MongoDB URL from .env
MONGO_URL = os.getenv("MONGO_URL")

# Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URL)

# Select our database
db = client.expense_tracker

# Collections we will use
expense_collection = db.expenses
salary_collection = db.salaries