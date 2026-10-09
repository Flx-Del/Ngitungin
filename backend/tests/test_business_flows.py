import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.expenses import create_expense, update_expense, void_expense
from app.api.products import adjust_stock, create_product, update_product
from app.api.transactions import create_other_income, create_sale, void_sale
from app.db.session import Base
from app.models import Business, Category, StockMovement, Transaction, User
from app.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    IncomeCreate,
    ProductCreate,
    ProductUpdate,
    SaleCreate,
    SaleItemInput,
    StockAdjustment,
)


class CoffeeShopFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine, expire_on_commit=False)()

        user = User(name="Pemilik Kedai", email="pemilik@example.test", password_hash="not-used")
        self.business = Business(business_name="Kedai Senja", business_type="Kedai kopi")
        user.businesses.append(self.business)
        self.session.add(user)
        self.session.flush()
        self.product_category = Category(
            business_id=self.business.id, name="Minuman", type="product"
        )
        self.expense_category = Category(
            business_id=self.business.id, name="Operasional", type="expense"
        )
        self.session.add_all([self.product_category, self.expense_category])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def make_product(self, name, sku, price, cost, stock):
        return create_product(
            ProductCreate(
                name=name,
                sku=sku,
                category_id=self.product_category.id,
                unit_label="gelas",
                selling_price=Decimal(price),
                cost_price=Decimal(cost),
                stock=Decimal(stock),
                minimum_stock=Decimal("2"),
            ),
            self.session,
            self.business,
        )

    def test_product_create_update_and_stock_adjustment(self):
        latte = self.make_product("  Kopi Susu Gula Aren  ", "KSA-001", "32000", "12000", "10")

        self.assertEqual(latte.name, "Kopi Susu Gula Aren")
        self.assertEqual(latte.stock, Decimal("10.000"))
        self.assertEqual(
            self.session.query(StockMovement).filter_by(product_id=latte.id).one().movement_type,
            "opening",
        )

        updated = update_product(
            latte.id,
            ProductUpdate(selling_price=Decimal("35000")),
            self.session,
            self.business,
        )
        self.assertEqual(updated.selling_price, Decimal("35000.00"))

        adjusted = adjust_stock(
            latte.id,
            StockAdjustment(quantity_change=Decimal("-2"), note="Stok rusak"),
            self.session,
            self.business,
        )
        self.assertEqual(adjusted.stock, Decimal("8.000"))
        with self.assertRaises(HTTPException) as error:
            adjust_stock(
                latte.id,
                StockAdjustment(quantity_change=Decimal("-9"), note="Koreksi stok"),
                self.session,
                self.business,
            )
        self.assertEqual(error.exception.status_code, 422)

    def test_expense_can_be_recorded_updated_and_voided(self):
        expense = create_expense(
            ExpenseCreate(
                expense_date=date(2026, 10, 1),
                amount=Decimal("450000"),
                description="  Tagihan listrik kedai  ",
                category_id=self.expense_category.id,
                payment_method="transfer",
                notes="Tagihan September",
            ),
            self.session,
            self.business,
        )
        self.assertEqual(expense.description, "Tagihan listrik kedai")

        updated = update_expense(
            expense.id,
            ExpenseUpdate(amount=Decimal("475000"), description="Tagihan listrik dan air"),
            self.session,
            self.business,
        )
        self.assertEqual(updated.amount, Decimal("475000.00"))
        self.assertEqual(updated.description, "Tagihan listrik dan air")

        void_expense(expense.id, self.session, self.business)
        self.assertEqual(expense.status, "void")
        with self.assertRaises(HTTPException) as error:
            update_expense(
                expense.id,
                ExpenseUpdate(amount=Decimal("500000")),
                self.session,
                self.business,
            )
        self.assertEqual(error.exception.status_code, 409)

    def test_coffee_sale_applies_discount_and_void_restores_stock(self):
        latte = self.make_product("Kopi Susu Gula Aren", "KSA-001", "35000", "12000", "10")
        americano = self.make_product("Americano", "AME-001", "25000", "8000", "8")
        sale = create_sale(
            SaleCreate(
                transaction_date=date(2026, 10, 2),
                items=[
                    SaleItemInput(product_id=latte.id, quantity=Decimal("2")),
                    SaleItemInput(product_id=americano.id, quantity=Decimal("1")),
                ],
                discount=Decimal("5000"),
                payment_method="qris",
                notes="Pesanan meja 4",
            ),
            self.session,
            self.business,
        )

        self.assertEqual(sale.type, "sale")
        self.assertEqual(sale.subtotal, Decimal("95000.00"))
        self.assertEqual(sale.total, Decimal("90000.00"))
        self.assertEqual(latte.stock, Decimal("8.000"))
        self.assertEqual(americano.stock, Decimal("7.000"))

        void_sale(sale.id, self.session, self.business)
        self.assertEqual(sale.status, "void")
        self.assertEqual(latte.stock, Decimal("10.000"))
        self.assertEqual(americano.stock, Decimal("8.000"))
        with self.assertRaises(HTTPException) as error:
            void_sale(sale.id, self.session, self.business)
        self.assertEqual(error.exception.status_code, 409)

    def test_sale_rejects_insufficient_stock_without_creating_transaction(self):
        latte = self.make_product("Kopi Susu Gula Aren", "KSA-001", "35000", "12000", "1")

        with self.assertRaises(HTTPException) as error:
            create_sale(
                SaleCreate(
                    transaction_date=date(2026, 10, 2),
                    items=[SaleItemInput(product_id=latte.id, quantity=Decimal("2"))],
                ),
                self.session,
                self.business,
            )
        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(latte.stock, Decimal("1.000"))
        self.assertEqual(self.session.query(Transaction).count(), 0)

    def test_other_income_is_recorded_as_non_sale(self):
        income = create_other_income(
            IncomeCreate(
                transaction_date=date(2026, 10, 3),
                amount=Decimal("150000"),
                description="Sewa ruang untuk komunitas kopi",
                payment_method="tunai",
            ),
            self.session,
            self.business,
        )

        self.assertEqual(income.type, "other_income")
        self.assertEqual(income.total, Decimal("150000.00"))
        self.assertEqual(income.description, "Sewa ruang untuk komunitas kopi")


if __name__ == "__main__":
    unittest.main()