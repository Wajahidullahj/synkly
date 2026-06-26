"""
main.py
-------------
Yeh file tumhare poore backend ka "entry point" hai.
Jab tum 'uvicorn main:app --reload' chalaoge, yahi file run hoti hai.

Yeh sab routes ko jodta hai aur server start karta hai.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
import models  # noqa: F401  (tables register karne ke liye import zaroori hai)
from routes import auth_routes, store_routes, shopify_routes

# Yeh line database mein saari tables bana degi (agar pehle se nahi hain)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Synkly API",
    description="TikTok Shop ↔ eCommerce sync platform — backend API",
    version="0.1.0",
)

# CORS — frontend (Next.js) ko backend se baat karne ki permission deta hai
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes ko app mein jodo
app.include_router(auth_routes.router)
app.include_router(store_routes.router)
app.include_router(shopify_routes.router)


@app.get("/")
def root():
    """Yeh check karne ke liye ke server zinda hai"""
    return {"message": "Synkly API is running 🚀"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
