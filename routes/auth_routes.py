"""
routes/auth_routes.py
-------------
Signup aur Login ke API endpoints yahan hain.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Naya user register karta hai"""

    # Check karo ke email already exist toh nahi karta
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Yeh email already registered hai")

    # Password hash karo (plain text kabhi save nahi karte)
    hashed_pw = auth.hash_password(user.password)

    new_user = models.User(
        email=user.email,
        hashed_password=hashed_pw,
        full_name=user.full_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """User login karta hai aur JWT token wapas milta hai"""

    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ya password galat hai")

    access_token = auth.create_access_token(data={"sub": str(user.id)})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    """Currently logged-in user ki details deta hai (token se pehchanta hai)"""
    return current_user
