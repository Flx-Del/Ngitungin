from datetime import date, datetime, timezone

from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    businesses: Mapped[list["Business"]] = relationship(back_populates="owner")


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    business_name: Mapped[str] = mapped_column(String(160))
    business_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    owner: Mapped[User] = relationship(back_populates="businesses")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(24), default="product")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    unit_label: Mapped[str] = mapped_column(String(40))
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    purchase_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProductMaterial(Base):
    __tablename__ = "product_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="RESTRICT"))
    quantity_used: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit_label: Mapped[str] = mapped_column(String(40))
    batch_yield: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("1"))


class LaborCost(Base):
    __tablename__ = "labor_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(160))
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    scope: Mapped[str] = mapped_column(String(16), default="per_batch")
    production_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("1"))


class OverheadCost(Base):
    __tablename__ = "overhead_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(160))
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    scope: Mapped[str] = mapped_column(String(16), default="per_batch")
    production_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("1"))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("business_id", "sku", name="uq_product_business_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    unit_label: Mapped[str] = mapped_column(String(40), default="unit")
    selling_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    stock: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0"))
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=True)
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(18, 3))
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    transaction_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(24), default="sale")
    status: Mapped[str] = mapped_column(String(16), default="posted")
    transaction_date: Mapped[date] = mapped_column(Date)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    payment_method: Mapped[str] = mapped_column(String(40), default="tunai")
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    items: Mapped[list["TransactionItem"]] = relationship(back_populates="transaction")


class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="RESTRICT"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=True)
    product_name_snapshot: Mapped[str] = mapped_column(String(160))
    sku_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3))
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    transaction: Mapped[Transaction] = relationship(back_populates="items")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True)
    expense_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    description: Mapped[str] = mapped_column(String(200))
    payment_method: Mapped[str] = mapped_column(String(40), default="tunai")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="posted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
