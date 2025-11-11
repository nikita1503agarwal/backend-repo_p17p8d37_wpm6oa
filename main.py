import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="SEYA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


def serialize(doc: dict):
    if not doc:
        return doc
    d = doc.copy()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert any nested ObjectIds (best-effort)
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d


# Schemas import for typing only
from schemas import Product as ProductSchema, Message as MessageSchema, BlogPost as BlogSchema, Order as OrderSchema


@app.get("/")
def root():
    return {"name": "SEYA API", "status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "Unknown"
            response["collections"] = db.list_collection_names()
    except Exception as e:
        response["database"] = f"⚠️ Error: {str(e)[:80]}"
    return response


# Products
@app.get("/api/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filter_query = {"active": True}
    if category:
        filter_query["category"] = category
    if q:
        filter_query["title"] = {"$regex": q, "$options": "i"}
    items = db["product"].find(filter_query).limit(100)
    return [serialize(x) for x in items]


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["product"].find_one({"_id": oid(product_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize(doc)


# Simple seed for demo
@app.post("/api/seed")
def seed():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    count = db["product"].count_documents({})
    if count > 0:
        return {"inserted": 0, "message": "Products already exist"}
    demo_products: List[ProductSchema] = [
        ProductSchema(
            title="SEYA Hoodie Noir",
            description="Hoodie premium en coton épais.",
            price=89.0,
            category="Hoodies",
            images=["https://images.unsplash.com/photo-1520975922203-b8ad5b1cfdf4"],
            tags=["nouveau", "best"],
            variants=[{"sku": "HD-BLK-S", "size": "S", "stock": 10}, {"sku": "HD-BLK-M", "size": "M", "stock": 15}],
            active=True,
        ),
        ProductSchema(
            title="SEYA Tee Crème",
            description="T-shirt oversize crème.",
            price=39.0,
            category="Tees",
            images=["https://images.unsplash.com/photo-1512436991641-6745cdb1723f"],
            tags=["drop"],
            variants=[{"sku": "TS-CRM-M", "size": "M", "stock": 25}],
            active=True,
        ),
        ProductSchema(
            title="SEYA Cargo Bleu",
            description="Cargo bleu électrique.",
            price=109.0,
            category="Pantalons",
            images=["https://images.unsplash.com/photo-1520975853989-5c2f5cb4831d"],
            tags=["limited"],
            variants=[{"sku": "CRG-BLU-32", "size": "32", "stock": 8}],
            active=True,
        ),
    ]
    inserted = 0
    for p in demo_products:
        create_document("product", p)
        inserted += 1
    return {"inserted": inserted}


# Contact
class ContactIn(BaseModel):
    name: str
    email: str
    subject: str
    message: str

@app.post("/api/contact")
def contact_submit(payload: ContactIn):
    try:
        from schemas import Message
        create_document("message", Message(**payload.model_dump()))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Blog
@app.get("/api/blog")
def list_blog(category: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    query = {"published": True}
    if category:
        query["category"] = category
    posts = db["blogpost"].find(query).sort("_id", -1).limit(50)
    return [serialize(x) for x in posts]


# Checkout with Stripe
class CartItem(BaseModel):
    product_id: str
    title: str
    quantity: int
    unit_price: float  # in EUR
    image: Optional[str] = None

class CheckoutIn(BaseModel):
    items: List[CartItem]
    currency: str = "eur"
    success_url: str
    cancel_url: str

@app.post("/api/checkout")
def create_checkout_session(payload: CheckoutIn):
    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=400, detail="Stripe not configured")
    try:
        import stripe
        stripe.api_key = secret
        line_items = [
            {
                "price_data": {
                    "currency": payload.currency,
                    "product_data": {
                        "name": i.title,
                        **({"images": [i.image]} if i.image else {}),
                    },
                    "unit_amount": int(round(i.unit_price * 100)),
                },
                "quantity": i.quantity,
            }
            for i in payload.items
        ]
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
        return {"id": session.id, "url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
