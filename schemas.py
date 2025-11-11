"""
Database Schemas for SEYA

Each Pydantic model maps to a MongoDB collection (lowercased class name).
These are used by the helper database layer and for validation in API routes.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr

# Users / Customers
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Hashed password")
    role: Literal["customer", "admin"] = Field("customer")
    phone: Optional[str] = None
    addresses: Optional[List[dict]] = Field(
        default=None,
        description="List of addresses (label, line1, line2, city, zip, country)"
    )
    is_active: bool = True

# Product variants (size, color, etc.)
class Variant(BaseModel):
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    stock: int = Field(ge=0, default=0)
    price: Optional[float] = Field(default=None, ge=0, description="Override price")

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: Literal["Hoodies", "Tees", "Pantalons", "Accessoires"]
    images: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    variants: List[Variant] = Field(default_factory=list)
    active: bool = True

# Orders
class OrderItem(BaseModel):
    product_id: str
    title: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)
    variant: Optional[dict] = None

class Order(BaseModel):
    user_email: Optional[EmailStr] = None
    items: List[OrderItem]
    currency: Literal["eur", "usd"] = "eur"
    subtotal: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    status: Literal["pending", "paid", "failed", "refunded"] = "pending"
    stripe_session_id: Optional[str] = None

# Blog/Actu posts
class BlogPost(BaseModel):
    title: str
    slug: str
    content: str
    category: Literal["drops", "collabs", "conseils"] = "drops"
    cover_image: Optional[str] = None
    published: bool = True

# Contact messages
class Message(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
    source: Literal["contact", "newsletter"] = "contact"

# Promo codes (for future admin)
class PromoCode(BaseModel):
    code: str
    type: Literal["percentage", "fixed"] = "percentage"
    value: float = Field(..., gt=0)
    active: bool = True
