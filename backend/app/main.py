from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.products import router as products_router
from app.api.transactions import router as transactions_router
from app.api.expenses import router as expenses_router
from app.api.costing import router as costing_router
from app.api.calculators import router as calculators_router
from app.api.reports import router as reports_router
from app.api.categories import router as categories_router
from app.core.config import settings
from app.db.session import Base, engine
from app import models  # noqa: F401 — register model metadata


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ngitungin API", version="0.1.0", description="API pembukuan dan HPP UMKM")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(transactions_router)
app.include_router(expenses_router)
app.include_router(costing_router)
app.include_router(calculators_router)
app.include_router(reports_router)
app.include_router(categories_router)


@app.get("/api/health", tags=["Sistem"])
def health():
    return {"status": "ok"}
