"""
routes/shopify_routes.py
-------------
Yeh file Shopify OAuth connection handle karti hai.

OAuth ka flow samjho ek "permission slip" jaisa:
1. User apna shop name deta hai (jaise: synkly-test.myshopify.com)
2. Hum usse Shopify ke login page pe bhejte hain ("yeh app aapke store ko access karna chahta hai, allow karte ho?")
3. User "Allow" pe click karta hai
4. Shopify humein wapas bhejta hai ek temporary "code" ke saath
5. Hum us code ko Shopify ko bhejte hain, badle mein humein "access_token" milta hai
6. Yeh access_token hum database mein save karte hain — ab hum is store ka data fetch kar sakte hain
"""

import os
import hmac
import hashlib
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
import models
import auth

router = APIRouter(prefix="/shopify", tags=["Shopify Integration"])

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
SCOPES = "read_products,write_products,read_inventory,write_inventory,read_orders,write_orders"

# Yeh wahi URL hai jo humne Shopify App settings mein "Allowed redirect URL" mein daala tha
REDIRECT_URI = "http://localhost:8000/shopify/callback"


@router.get("/install")
def shopify_install(shop: str, user_id: int, db: Session = Depends(get_db)):
    """
    STEP 1 — User yahan se shuru karta hai.
    Example call: /shopify/install?shop=synkly-test.myshopify.com&user_id=1

    Yeh user ko Shopify ke authorization page pe bhej deta hai.
    """
    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Shop URL aise hona chahiye: yourstore.myshopify.com")

    # State mein user_id chhupate hain — taake callback mein pata chale yeh kis user ke liye hai
    state = str(user_id)

    install_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={SHOPIFY_API_KEY}"
        f"&scope={SCOPES}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={state}"
    )

    return {"install_url": install_url}


@router.get("/callback")
def shopify_callback(request: Request, db: Session = Depends(get_db)):
    """
    STEP 2 — Shopify user ko yahan wapas bhejta hai "Allow" click karne ke baad.

    Query params mein milta hai:
    - code: temporary code jo access_token mein convert hoga
    - shop: konsa store hai
    - state: humara bheja hua user_id
    - hmac: security verification ke liye
    """
    params = dict(request.query_params)
    code = params.get("code")
    shop = params.get("shop")
    state = params.get("state")  # yeh user_id hai

    if not code or not shop:
        raise HTTPException(status_code=400, detail="Shopify se zaroori data nahi mila")

    # Security check — verify karo ke yeh request actually Shopify se aayi hai (HMAC verification)
    if not verify_hmac(params):
        raise HTTPException(status_code=400, detail="Security verification fail hui — request trusted nahi hai")

    # STEP 3 — Code ko access_token mein convert karo
    token_response = requests.post(
        f"https://{shop}/admin/oauth/access_token",
        json={
            "client_id": SHOPIFY_API_KEY,
            "client_secret": SHOPIFY_API_SECRET,
            "code": code,
        },
    )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Shopify se access token nahi mila")

    access_token = token_response.json().get("access_token")

    # STEP 4 — Database mein save karo
    user_id = int(state)
    existing_store = (
        db.query(models.Store)
        .filter(models.Store.user_id == user_id, models.Store.shop_url == shop)
        .first()
    )

    if existing_store:
        existing_store.access_token = access_token
        existing_store.is_connected = True
    else:
        new_store = models.Store(
            user_id=user_id,
            platform="shopify",
            shop_url=shop,
            access_token=access_token,
            is_connected=True,
        )
        db.add(new_store)

    db.commit()

    return {"message": f"{shop} successfully connect ho gaya! 🎉"}


def verify_hmac(params: dict) -> bool:
    """
    Yeh check karta hai ke request Shopify se hi aayi hai, kisi fake source se nahi.
    Shopify har request ke saath ek 'signature' (hmac) bhejta hai jo hum verify karte hain.
    """
    received_hmac = params.pop("hmac", None)
    if not received_hmac:
        return False

    sorted_params = "&".join(f"{key}={value}" for key, value in sorted(params.items()))

    calculated_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode("utf-8"),
        sorted_params.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(calculated_hmac, received_hmac)


@router.get("/products/{store_id}")
def fetch_shopify_products(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Connected Shopify store se products fetch karta hai aur database mein save karta hai.
    """
    store = (
        db.query(models.Store)
        .filter(models.Store.id == store_id, models.Store.user_id == current_user.id)
        .first()
    )

    if not store or not store.is_connected:
        raise HTTPException(status_code=404, detail="Store nahi mila ya connected nahi hai")

    response = requests.get(
        f"https://{store.shop_url}/admin/api/2024-10/products.json",
        headers={"X-Shopify-Access-Token": store.access_token},
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Shopify se products fetch nahi ho paaye")

    shopify_products = response.json().get("products", [])

    saved_count = 0
    for sp in shopify_products:
        # Pehle check karo yeh product already database mein hai ya nahi
        existing = (
            db.query(models.Product)
            .filter(models.Product.platform_product_id == str(sp["id"]), models.Product.store_id == store.id)
            .first()
        )
        if existing:
            continue

        variant = sp["variants"][0] if sp.get("variants") else {}

        new_product = models.Product(
            store_id=store.id,
            title=sp.get("title", "Untitled"),
            description=sp.get("body_html", ""),
            price=float(variant.get("price", 0)) if variant.get("price") else 0,
            sku=variant.get("sku"),
            quantity=variant.get("inventory_quantity", 0),
            platform_product_id=str(sp["id"]),
        )
        db.add(new_product)
        saved_count += 1

    db.commit()

    return {"message": f"{saved_count} naye products database mein save hue", "total_fetched": len(shopify_products)}
