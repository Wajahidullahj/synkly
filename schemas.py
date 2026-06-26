"""
schemas.py
-------------
Yeh file define karti hai ke API request/response mein
data kaise dikhna chahiye. Models.py "database" ke liye hai,
schemas.py "API ke andar aana-jaana" ke liye hai.

Example: jab koi signup karega, hum check karna chahte hain
ke email valid hai, password kam se kam itne characters ka hai, etc.
Yeh validation Pydantic automatically karta hai.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# ---------- USER SCHEMAS ----------

class UserCreate(BaseModel):
    """Jab naya user signup karega, yeh data aayega"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Login ke time yeh data aayega"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User ka data jo hum response mein wapas bhejenge (password kabhi nahi bhejte!)"""
    id: int
    email: str
    full_name: Optional[str]
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy model se directly convert karne ke liye


class Token(BaseModel):
    """Login successful hone ke baad yeh token wapas milega"""
    access_token: str
    token_type: str = "bearer"


# ---------- STORE SCHEMAS ----------

class StoreCreate(BaseModel):
    platform: str
    shop_url: Optional[str] = None


class StoreResponse(BaseModel):
    id: int
    platform: str
    shop_url: Optional[str]
    is_connected: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- PRODUCT SCHEMAS ----------

class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: Optional[float] = None
    sku: Optional[str] = None
    quantity: int = 0


class ProductResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: Optional[float]
    sku: Optional[str]
    quantity: int
    created_at: datetime

    class Config:
        from_attributes = True
