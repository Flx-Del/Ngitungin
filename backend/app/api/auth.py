from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Business, Category, User
from app.schemas import AuthResponse, BusinessResponse, LoginRequest, RegisterRequest, UserResponse


router = APIRouter(prefix="/api/auth", tags=["Akun"])


def response_for(user: User, business: Business) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            business=BusinessResponse.model_validate(business),
        ),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    exists = db.query(User).filter(func.lower(User.email) == email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email tersebut sudah terdaftar.")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    business = Business(
        business_name=payload.business_name.strip(),
        business_type=payload.business_type.strip() if payload.business_type else None,
    )
    user.businesses.append(business)
    db.add(user)
    db.flush()
    for category_name in ("Bahan baku", "Gaji", "Listrik", "Air", "Internet", "Sewa", "Transportasi", "Marketing", "Packaging", "Operasional", "Lainnya"):
        db.add(Category(business_id=business.id, name=category_name, type="expense"))
    db.add(Category(business_id=business.id, name="Umum", type="product"))
    db.commit()
    db.refresh(user)
    db.refresh(business)
    return response_for(user, business)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau kata sandi tidak cocok.")
    business = db.query(Business).filter(Business.user_id == user.id).order_by(Business.id).first()
    if business is None:
        raise HTTPException(status_code=403, detail="Profil usaha belum tersedia.")
    return response_for(user, business)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.user_id == user.id).order_by(Business.id).first()
    if business is None:
        raise HTTPException(status_code=403, detail="Profil usaha belum tersedia.")
    return UserResponse(id=user.id, name=user.name, email=user.email, business=BusinessResponse.model_validate(business))
