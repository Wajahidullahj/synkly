"""
models.py
-------------
Yeh file database ke "tables" define karti hai.
Har class ek table hai. Har class ke andar variables = table ke columns.

Jab hum app run karenge, SQLAlchemy automatically yeh tables
PostgreSQL mein bana dega — humein manually SQL likhne ki zaroorat nahi.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """Tumhare platform ke users (jo log Synkly use karenge)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Google se login karne walon ka password nahi hota
    full_name = Column(String, nullable=True)
    plan = Column(String, default="free")  # free, starter, growth, pro
    is_active = Column(Boolean, default=True)
    auth_provider = Column(String, default="local")  # "local" (email/password) ya "google"
    google_id = Column(String, unique=True, nullable=True, index=True)
    avatar_url = Column(String, nullable=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Ek user ke multiple stores ho sakte hain (Shopify, TikTok, etc.)
    stores = relationship("Store", back_populates="owner")


class Store(Base):
    """Connected stores — Shopify, TikTok Shop, Amazon, etc."""
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    platform = Column(String, nullable=False)  # "shopify", "tiktok", "amazon"
    shop_url = Column(String, nullable=True)
    access_token = Column(String, nullable=True)  # encrypted store karna baad mein
    is_connected = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="stores")
    products = relationship("Product", back_populates="store")


class Product(Base):
    """Products jo sync ho rahe hain platforms ke beech"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    sku = Column(String, nullable=True)
    quantity = Column(Integer, default=0)
    platform_product_id = Column(String, nullable=True)  # original platform ka product ID
    tiktok_product_id = Column(String, nullable=True)    # TikTok pe sync hone ke baad ka ID
    last_synced = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    store = relationship("Store", back_populates="products")


class Order(Base):
    """Orders jo TikTok Shop ya doosre platforms se aate hain"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    platform_order_id = Column(String, nullable=False)
    customer_name = Column(String, nullable=True)
    total_amount = Column(Float, nullable=True)
    status = Column(String, default="pending")  # pending, fulfilled, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SyncLog(Base):
    """Har sync attempt ka record — kya hua, kya fail hua (debugging ke liye)"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    action = Column(String, nullable=False)  # "product_sync", "order_sync", etc.
    status = Column(String, nullable=False)  # "success", "failed"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
