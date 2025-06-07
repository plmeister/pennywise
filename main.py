# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routers import auth, transactions, accounts, forecast, scheduled, categories

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pennywise",
    description="A friendly and modular personal budgeting app that helps you track, forecast, and manage your finances with precision.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(forecast.router)
app.include_router(scheduled.router)
app.include_router(categories.router)
