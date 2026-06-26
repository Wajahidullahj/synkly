"""
routes/store_routes.py
-------------
Stores connect karne aur list karne ke endpoints.
(Abhi yeh basic hai — Shopify/TikTok ka actual OAuth Phase 2/3 mein aayega)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/stores", tags=["Stores"])


@router.post("/", response_model=schemas.StoreResponse)
def connect_store(
    store: schemas.StoreCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Naya store connect karta hai (abhi sirf record banata hai, real OAuth baad mein)"""
    new_store = models.Store(
        user_id=current_user.id,
        platform=store.platform,
        shop_url=store.shop_url,
    )
    db.add(new_store)
    db.commit()
    db.refresh(new_store)
    return new_store


@router.get("/", response_model=List[schemas.StoreResponse])
def list_my_stores(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Logged-in user ke saare connected stores dikhata hai"""
    return db.query(models.Store).filter(models.Store.user_id == current_user.id).all()
