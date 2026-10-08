from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.models import Business, LaborCost, Material, OverheadCost, Product, ProductMaterial
from app.schemas import CostingResponse, CostingUpdate, MaterialCreate, MaterialResponse
from app.services.units import ingredient_cost_per_unit, units_compatible


router = APIRouter(tags=["Kalkulator HPP"])
CENT = Decimal("0.01")


@router.get("/api/materials", response_model=list[MaterialResponse])
def list_materials(db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    return db.query(Material).filter(Material.business_id == business.id, Material.is_active.is_(True)).order_by(Material.name).all()


@router.post("/api/materials", response_model=MaterialResponse, status_code=201)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    if not payload.name.strip() or not payload.unit_label.strip():
        raise HTTPException(status_code=422, detail="Nama bahan dan satuan wajib diisi.")
    values = payload.model_dump()
    values["name"] = payload.name.strip()
    values["unit_label"] = payload.unit_label.strip()
    material = Material(business_id=business.id, **values)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.put("/api/products/{product_id}/costing", response_model=CostingResponse)
def update_costing(product_id: int, payload: CostingUpdate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    product = db.query(Product).filter(Product.id == product_id, Product.business_id == business.id).with_for_update().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    ids = {entry.material_id for entry in payload.ingredients}
    materials = db.query(Material).filter(
        Material.business_id == business.id, Material.is_active.is_(True), Material.id.in_(ids)
    ).all() if ids else []
    by_id = {material.id: material for material in materials}
    if len(by_id) != len(ids):
        raise HTTPException(status_code=422, detail="Bahan tidak ditemukan atau bukan milik usaha Anda.")
    for entry in payload.ingredients:
        if not units_compatible(by_id[entry.material_id].unit_label, entry.unit_label):
            raise HTTPException(status_code=422, detail=f"Satuan bahan {by_id[entry.material_id].name} tidak kompatibel dengan satuan resep.")
    if payload.batch_yield <= 0:
        raise HTTPException(status_code=422, detail="Jumlah hasil produksi harus lebih dari nol.")

    db.query(ProductMaterial).filter(ProductMaterial.product_id == product.id).delete()
    db.query(LaborCost).filter(LaborCost.product_id == product.id).delete()
    db.query(OverheadCost).filter(OverheadCost.product_id == product.id).delete()
    for entry in payload.ingredients:
        db.add(ProductMaterial(
            product_id=product.id, material_id=entry.material_id,
            quantity_used=entry.quantity_used, unit_label=entry.unit_label,
            batch_yield=payload.batch_yield,
        ))
    for entry in payload.labor:
        db.add(LaborCost(product_id=product.id, **entry.model_dump()))
    for entry in payload.overhead:
        db.add(OverheadCost(product_id=product.id, **entry.model_dump()))
    db.flush()

    ingredient_rows = db.query(ProductMaterial, Material).join(Material, ProductMaterial.material_id == Material.id).filter(
        ProductMaterial.product_id == product.id
    ).all()
    material_total = sum((
        ingredient_cost_per_unit(
            material.purchase_price, material.purchase_quantity, recipe.quantity_used,
            recipe.unit_label, material.unit_label, payload.batch_yield,
        )
        for recipe, material in ingredient_rows
    ), Decimal("0"))
    labor_total = _component_unit_cost(db.query(LaborCost).filter(LaborCost.product_id == product.id).all())
    overhead_total = _component_unit_cost(db.query(OverheadCost).filter(OverheadCost.product_id == product.id).all())
    material_total = material_total.quantize(CENT, rounding=ROUND_HALF_UP)
    labor_total = labor_total.quantize(CENT, rounding=ROUND_HALF_UP)
    overhead_total = overhead_total.quantize(CENT, rounding=ROUND_HALF_UP)
    product.cost_price = material_total + labor_total + overhead_total
    db.commit()
    return CostingResponse(
        product_id=product.id, batch_yield=payload.batch_yield,
        material_cost_per_unit=material_total, labor_cost_per_unit=labor_total,
        overhead_cost_per_unit=overhead_total, total_cost_per_unit=product.cost_price,
    )


def _component_unit_cost(components) -> Decimal:
    total = Decimal("0")
    for component in components:
        if component.scope == "per_unit":
            total += component.cost
        else:
            # Per-batch and per-month components are apportioned using the production quantity supplied.
            total += component.cost / component.production_quantity
    return total


@router.get("/api/products/{product_id}/costing", response_model=CostingResponse)
def get_costing(product_id: int, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    product = db.query(Product).filter(Product.id == product_id, Product.business_id == business.id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    recipes = db.query(ProductMaterial).filter(ProductMaterial.product_id == product.id).all()
    batch_yield = recipes[0].batch_yield if recipes else Decimal("1")
    material_rows = db.query(ProductMaterial, Material).join(Material, ProductMaterial.material_id == Material.id).filter(
        ProductMaterial.product_id == product.id
    ).all()
    material_total = sum((
        ingredient_cost_per_unit(
            material.purchase_price, material.purchase_quantity, recipe.quantity_used,
            recipe.unit_label, material.unit_label, batch_yield,
        )
        for recipe, material in material_rows
    ), Decimal("0"))
    labor_total = _component_unit_cost(db.query(LaborCost).filter(LaborCost.product_id == product.id).all())
    overhead_total = _component_unit_cost(db.query(OverheadCost).filter(OverheadCost.product_id == product.id).all())
    return CostingResponse(
        product_id=product.id, batch_yield=batch_yield,
        material_cost_per_unit=material_total.quantize(CENT, rounding=ROUND_HALF_UP),
        labor_cost_per_unit=labor_total.quantize(CENT, rounding=ROUND_HALF_UP),
        overhead_cost_per_unit=overhead_total.quantize(CENT, rounding=ROUND_HALF_UP),
        total_cost_per_unit=product.cost_price,
    )
