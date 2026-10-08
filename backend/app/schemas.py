from datetime import date
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    business_name: str = Field(min_length=2, max_length=160)
    business_type: str | None = Field(default=None, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class BusinessResponse(BaseModel):
    id: int
    business_name: str
    business_type: str | None
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    business: BusinessResponse


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str | None = Field(default=None, max_length=80)
    category_id: int | None = Field(default=None, gt=0)
    unit_label: str = Field(default="unit", min_length=1, max_length=40)
    selling_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    cost_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    stock: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=3)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=3)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    sku: str | None = Field(default=None, max_length=80)
    category_id: int | None = Field(default=None, gt=0)
    unit_label: str | None = Field(default=None, min_length=1, max_length=40)
    selling_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    minimum_stock: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=3)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str | None
    category_id: int | None
    unit_label: str
    selling_price: Decimal
    cost_price: Decimal
    stock: Decimal
    minimum_stock: Decimal
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    quantity_change: Decimal = Field(ne=0, max_digits=18, decimal_places=3)
    note: str = Field(min_length=2, max_length=200)


class SaleItemInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)


class SaleCreate(BaseModel):
    transaction_date: date
    items: list[SaleItemInput] = Field(min_length=1, max_length=100)
    discount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    payment_method: str = Field(default="tunai", min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)


class ExpenseCreate(BaseModel):
    expense_date: date
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    description: str = Field(min_length=1, max_length=200)
    category_id: int | None = Field(default=None, gt=0)
    payment_method: str = Field(default="tunai", min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)


class ExpenseUpdate(BaseModel):
    expense_date: date | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    description: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = Field(default=None, gt=0)
    payment_method: str | None = Field(default=None, min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)


class ExpenseResponse(BaseModel):
    id: int
    expense_date: date
    amount: Decimal
    description: str
    category_id: int | None
    payment_method: str
    notes: str | None
    status: str
    model_config = ConfigDict(from_attributes=True)


class IncomeCreate(BaseModel):
    transaction_date: date
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    description: str = Field(min_length=1, max_length=200)
    payment_method: str = Field(default="tunai", min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)


class TransactionItemResponse(BaseModel):
    product_id: int | None
    product_name_snapshot: str
    quantity: Decimal
    price: Decimal
    cost_per_unit: Decimal
    subtotal: Decimal
    discount: Decimal
    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    id: int
    transaction_number: str
    transaction_date: date
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    payment_method: str
    type: str
    description: str | None
    notes: str | None
    status: str
    items: list[TransactionItemResponse]


class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    unit_label: str = Field(min_length=1, max_length=40)
    purchase_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    purchase_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class MaterialResponse(BaseModel):
    id: int
    name: str
    unit_label: str
    purchase_price: Decimal
    purchase_quantity: Decimal
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class CostingIngredient(BaseModel):
    material_id: int = Field(gt=0)
    quantity_used: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit_label: str = Field(min_length=1, max_length=40)


class CostComponent(BaseModel):
    description: str = Field(min_length=1, max_length=160)
    cost: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    scope: str = Field(default="per_batch", pattern="^(per_unit|per_batch|per_month)$")
    production_quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=18, decimal_places=3)


class CostingUpdate(BaseModel):
    batch_yield: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    ingredients: list[CostingIngredient] = Field(default_factory=list, max_length=100)
    labor: list[CostComponent] = Field(default_factory=list, max_length=50)
    overhead: list[CostComponent] = Field(default_factory=list, max_length=50)


class CostingResponse(BaseModel):
    product_id: int
    batch_yield: Decimal
    material_cost_per_unit: Decimal
    labor_cost_per_unit: Decimal
    overhead_cost_per_unit: Decimal
    total_cost_per_unit: Decimal


class PriceSuggestionRequest(BaseModel):
    product_id: int = Field(gt=0)
    target_margin: Decimal = Field(ge=0, lt=1, max_digits=5, decimal_places=4)
    rounding: Literal[100, 500, 1000] = 100


class PriceSuggestionResponse(BaseModel):
    product_id: int
    cost_per_unit: Decimal
    target_margin: Decimal
    minimum_price: Decimal
    suggested_price: Decimal
    estimated_profit: Decimal


class ProfitSimulationRequest(BaseModel):
    product_id: int = Field(gt=0)
    selling_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    quantity_sold: Decimal = Field(gt=0, max_digits=18, decimal_places=3)


class ProfitSimulationResponse(BaseModel):
    product_id: int
    quantity_sold: Decimal
    revenue: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    margin: Decimal
