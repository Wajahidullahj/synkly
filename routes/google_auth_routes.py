"""
routes/google_auth_routes.py
-------------
Yeh file "Continue with Google" feature handle karti hai.

Flow samjho:
1. User "Continue with Google" pe click karta hai
2. Hum usse Google ke login page pe bhejte hain
3. User apna Google account select karta hai, permission deta hai
4. Google humein wapas bhejta hai ek "code" ke saath
5. Hum us code ko Google ko bhejte hain, badle mein humein user ki email/naam milta hai
6. Agar yeh email pehle se database mein hai -> login kar do
   Agar nahi hai -> naya account bana do (bina password ke)
7. Apna khud ka JWT token generate karke do (jaisa normal login mein hota hai)
"""

import os
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
import models
import auth

router = APIRouter(prefix="/auth/google", tags=["Google Login"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Yeh wahi redirect URI hai jo humne Google Cloud Console mein register ki thi
# .env mein BACKEND_URL set karo: local mein http://localhost:8000, production mein Railway URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REDIRECT_URI = f"{BACKEND_URL}/auth/google/callback"

# Jahan login successful hone ke baad user ko bhejna hai (dashboard)
# .env mein FRONTEND_URL set karo: local mein file path, production mein Netlify URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")
FRONTEND_SUCCESS_URL = f"{FRONTEND_URL}/dashboard.html"


@router.get("/login")
def google_login():
    """
    STEP 1 — Frontend ka "Continue with Google" button isi endpoint ko call karega.
    Yeh user ko Google ke authorization page pe bhej deta hai.
    """
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid email profile"
        "&access_type=offline"
        "&prompt=select_account"
    )
    return RedirectResponse(google_auth_url)


@router.get("/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    """
    STEP 2 — Google user ko yahan wapas bhejta hai "Allow" click karne ke baad.
    Query param mein milta hai 'code', jisse humein access_token milega Google se.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Google se code nahi mila")

    # STEP 3 — Code ko Google ke access_token mein convert karo
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
    )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Google se access token nahi mila")

    google_token = token_response.json().get("access_token")

    # STEP 4 — Us access_token se Google se user ki profile info mango
    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {google_token}"},
    )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Google se profile info nahi mili")

    profile = userinfo_response.json()
    google_id = profile.get("id")
    email = profile.get("email")
    full_name = profile.get("name")
    avatar_url = profile.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google account se email nahi mili")

    # STEP 5 — Check karo yeh user pehle se database mein hai ya nahi
    user = db.query(models.User).filter(models.User.email == email).first()

    if user:
        # Pehle se account hai — agar Google id missing hai, update kar do (link kar do)
        if not user.google_id:
            user.google_id = google_id
            user.auth_provider = "google"
            user.avatar_url = avatar_url
            db.commit()
    else:
        # Naya user banao — koi password nahi, kyunki Google se login ho rahi hai
        user = models.User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            avatar_url=avatar_url,
            auth_provider="google",
            is_email_verified=True,  # Google ne already email verify ki hai
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # STEP 6 — Apna khud ka JWT token generate karo (jaisa normal login mein hota hai)
    access_token = auth.create_access_token(data={"sub": str(user.id)})

    # STEP 7 — Frontend pe redirect karo, token ke saath
    # (token URL mein bhejna ideal nahi hota production mein, lekin abhi ke liye simplest tareeka hai)
    return RedirectResponse(f"{FRONTEND_SUCCESS_URL}?token={access_token}")
