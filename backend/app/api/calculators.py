from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.models import Business, Product
from app.schemas import (
    PriceSuggestionRequest, PriceSuggestionResponse,
    ProfitSimulationRequest, ProfitSimulationResponse,
)
from app.services.pricing import simulate_profit, suggest_price


router = APIRouter(prefix="/api/calculators", tags=["Kalkulator"])
@router.post("/price", response_model=PriceSuggestionResponse)
def suggest_price(payload: PriceSuggestionRequest, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    product = db.query(Product).filter(Product.id == payload.product_id, Product.business_id == business.id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    cost = product.cost_price
    minimum, suggested, estimated_profit = suggest_price(cost, payload.target_margin, payload.rounding)
    return PriceSuggestionResponse(
        product_id=product.id, cost_per_unit=cost, target_margin=payload.target_margin,
        minimum_price=minimum, suggested_price=suggested,
        estimated_profit=estimated_profit,
    )


@router.post("/profit-simulation", response_model=ProfitSimulationResponse)
def simulate_profit(payload: ProfitSimulationRequest, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    product = db.query(Product).filter(Product.id == payload.product_id, Product.business_id == business.id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    revenue, total_cost, profit, margin = simulate_profit(product.cost_price, payload.selling_price, payload.quantity_sold)
    return ProfitSimulationResponse(
        product_id=product.id, quantity_sold=payload.quantity_sold,
        revenue=revenue, total_cost=total_cost, gross_profit=profit, margin=margin,
    )
