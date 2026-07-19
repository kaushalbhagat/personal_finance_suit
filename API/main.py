# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import categories, mappings, transactions, plaid, accounts, tools
from contextlib import asynccontextmanager
from database import engine, init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the server starts up
    await init_db(engine)
    yield
    # This runs when the server shuts down (if needed)

app = FastAPI(
    title="💰 Unified Personal Budget API Hub",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS safely for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔌 REGISTER YOUR ROUTER MODULES
app.include_router(categories.router)
app.include_router(mappings.router)
app.include_router(transactions.router)
app.include_router(plaid.router)
app.include_router(accounts.router)
app.include_router(tools.router)

@app.get("/")
def root_check():
    return {"status": "healthy", "service": "budget-ledger-core"}