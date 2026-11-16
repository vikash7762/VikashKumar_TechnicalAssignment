from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    category: str = Field(default="General", min_length=1, max_length=100)
    price: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    price: Optional[Decimal] = Field(default=None, ge=Decimal("0"), max_digits=10, decimal_places=2)


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: Optional[str] = None
    category: str
    price: Decimal
    stock_quantity: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    movement_type: Literal["in", "out"]
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("A meaningful stock adjustment reason is required")
        return value


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class SalesOrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    items: list[OrderItemCreate] = Field(min_length=1)
    discount_percentage: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0"), le=Decimal("20"),
        max_digits=5, decimal_places=2
    )


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    model_config = ConfigDict(from_attributes=True)


class SalesOrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    created_by: int
    subtotal: Decimal
    discount_percentage: Decimal
    discount_amount: Decimal
    grand_total: Decimal
    total_amount: Decimal
    status: str
    items: list[OrderItemResponse]
    model_config = ConfigDict(from_attributes=True)
