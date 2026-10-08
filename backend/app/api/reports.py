import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.models import Business, Expense, Product, Transaction, TransactionItem


router = APIRouter(prefix="/api", tags=["Dashboard dan Laporan"])


@router.get("/dashboard")
def dashboard(start: date, end: date, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    if end < start:
        raise HTTPException(status_code=422, detail="Tanggal akhir harus sama atau setelah tanggal awal.")
    if (end - start).days > 366:
        raise HTTPException(status_code=422, detail="Pilih rentang laporan paling lama satu tahun.")
    sales = db.query(func.coalesce(func.sum(Transaction.total), 0)).filter(
        Transaction.business_id == business.id, Transaction.type == "sale", Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).scalar()
    other_income = db.query(func.coalesce(func.sum(Transaction.total), 0)).filter(
        Transaction.business_id == business.id, Transaction.type == "other_income", Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).scalar()
    operating_expenses = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.business_id == business.id, Expense.status == "posted",
        Expense.expense_date >= start, Expense.expense_date <= end,
    ).scalar()
    cogs = db.query(func.coalesce(func.sum(TransactionItem.quantity * TransactionItem.cost_per_unit), 0)).join(
        Transaction, TransactionItem.transaction_id == Transaction.id
    ).filter(
        Transaction.business_id == business.id, Transaction.type == "sale", Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).scalar()
    tx_count = db.query(func.count(Transaction.id)).filter(
        Transaction.business_id == business.id, Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).scalar()
    top_products = db.query(
        TransactionItem.product_name_snapshot,
        func.sum(TransactionItem.quantity).label("quantity"),
    ).join(Transaction, TransactionItem.transaction_id == Transaction.id).filter(
        Transaction.business_id == business.id, Transaction.type == "sale", Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).group_by(TransactionItem.product_name_snapshot).order_by(func.sum(TransactionItem.quantity).desc()).limit(5).all()
    low_stock = db.query(Product).filter(
        Product.business_id == business.id, Product.is_active.is_(True), Product.stock <= Product.minimum_stock
    ).order_by(Product.stock).limit(10).all()
    daily_sales = db.query(
        Transaction.transaction_date, func.sum(Transaction.total).label("total")
    ).filter(
        Transaction.business_id == business.id, Transaction.type == "sale", Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).group_by(Transaction.transaction_date).order_by(Transaction.transaction_date).all()
    daily_expenses = db.query(
        Expense.expense_date, func.sum(Expense.amount).label("total")
    ).filter(
        Expense.business_id == business.id, Expense.status == "posted",
        Expense.expense_date >= start, Expense.expense_date <= end,
    ).group_by(Expense.expense_date).all()
    daily_other_income = db.query(
        Transaction.transaction_date, func.sum(Transaction.total).label("total")
    ).filter(
        Transaction.business_id == business.id, Transaction.type == "other_income", Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).group_by(Transaction.transaction_date).all()
    daily_costs = db.query(
        Transaction.transaction_date, func.sum(TransactionItem.quantity * TransactionItem.cost_per_unit).label("total")
    ).join(TransactionItem, TransactionItem.transaction_id == Transaction.id).filter(
        Transaction.business_id == business.id, Transaction.type == "sale", Transaction.status == "posted",
        Transaction.transaction_date >= start, Transaction.transaction_date <= end,
    ).group_by(Transaction.transaction_date).all()
    sales = Decimal(str(sales))
    other_income = Decimal(str(other_income))
    cogs = Decimal(str(cogs))
    operating_expenses = Decimal(str(operating_expenses))
    sales_by_day = {row[0]: Decimal(str(row[1])) for row in daily_sales}
    other_income_by_day = {row[0]: Decimal(str(row[1])) for row in daily_other_income}
    expenses_by_day = {row[0]: Decimal(str(row[1])) for row in daily_expenses}
    costs_by_day = {row[0]: Decimal(str(row[1])) for row in daily_costs}
    financial_trend = []
    current_date = start
    while current_date <= end:
        day_sales = sales_by_day.get(current_date, Decimal("0"))
        day_other_income = other_income_by_day.get(current_date, Decimal("0"))
        day_expenses = expenses_by_day.get(current_date, Decimal("0"))
        day_cost = costs_by_day.get(current_date, Decimal("0"))
        financial_trend.append({
            "date": current_date,
            "sales": day_sales + day_other_income,
            "expenses": day_expenses,
            "profit": day_sales + day_other_income - day_cost - day_expenses,
        })
        current_date += timedelta(days=1)
    return {
        "period": {"start": start, "end": end},
        "total_sales": sales,
        "other_income": other_income,
        "total_expenses": operating_expenses,
        "total_cost_of_goods": cogs,
        "net_profit": sales + other_income - cogs - operating_expenses,
        "transaction_count": tx_count,
        "best_sellers": [{"name": row[0], "quantity": row[1]} for row in top_products],
        "low_stock": [{"id": p.id, "name": p.name, "stock": p.stock, "minimum_stock": p.minimum_stock} for p in low_stock],
        "daily_sales": [{"date": row[0], "total": row[1]} for row in daily_sales],
        "financial_trend": financial_trend,
    }


@router.get("/reports/income-statement")
def income_statement(start: date, end: date, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    summary = dashboard(start, end, db, business)
    return {
        "period": summary["period"],
        "sales_revenue": summary["total_sales"],
        "other_income": summary["other_income"],
        "cost_of_goods": summary["total_cost_of_goods"],
        "operating_expenses": summary["total_expenses"],
        "net_profit": summary["net_profit"],
    }


@router.get("/reports/product-costing")
def product_costing(db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    products = db.query(Product).filter(Product.business_id == business.id).order_by(Product.name).all()
    return [{
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "cost_price": product.cost_price,
        "selling_price": product.selling_price,
        "profit": product.selling_price - product.cost_price,
        "margin": (product.selling_price - product.cost_price) / product.selling_price if product.selling_price else Decimal("0"),
    } for product in products]


@router.get("/reports/export.csv")
def export_transactions(start: date, end: date, dataset: str = "transactions", db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    if end < start:
        raise HTTPException(status_code=422, detail="Tanggal akhir harus sama atau setelah tanggal awal.")
    stream = io.StringIO()
    writer = csv.writer(stream)
    if dataset == "transactions":
        rows = db.query(Transaction).filter(
            Transaction.business_id == business.id, Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        ).order_by(Transaction.transaction_date, Transaction.id).all()
        writer.writerow(["Nomor transaksi", "Tanggal", "Jenis", "Status", "Subtotal", "Diskon", "Total", "Metode pembayaran"])
        for row in rows:
            writer.writerow([row.transaction_number, row.transaction_date.strftime("%d/%m/%Y"), row.type, row.status, row.subtotal, row.discount, row.total, row.payment_method])
    elif dataset == "expenses":
        rows = db.query(Expense).filter(
            Expense.business_id == business.id, Expense.expense_date >= start,
            Expense.expense_date <= end,
        ).order_by(Expense.expense_date, Expense.id).all()
        writer.writerow(["Tanggal", "Deskripsi", "Nominal", "Metode pembayaran", "Status"])
        for row in rows:
            writer.writerow([row.expense_date.strftime("%d/%m/%Y"), row.description, row.amount, row.payment_method, row.status])
    elif dataset == "product-costing":
        rows = db.query(Product).filter(Product.business_id == business.id, Product.is_active.is_(True)).order_by(Product.name).all()
        writer.writerow(["Produk", "SKU", "HPP", "Harga jual", "Laba per unit", "Margin"])
        for row in rows:
            profit = row.selling_price - row.cost_price
            margin = profit / row.selling_price if row.selling_price else Decimal("0")
            writer.writerow([row.name, row.sku or "", row.cost_price, row.selling_price, profit, f"{margin:.4%}"])
    else:
        raise HTTPException(status_code=422, detail="Jenis ekspor tidak dikenal.")
    stream.seek(0)
    filename = f"{dataset}-{start:%Y%m%d}-{end:%Y%m%d}.csv"
    return StreamingResponse(
        iter(["\ufeff" + stream.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
