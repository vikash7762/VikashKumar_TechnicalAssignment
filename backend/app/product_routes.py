from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import Product, StockMovement
from app.schemas import ProductCreate, ProductUpdate, ProductResponse, StockAdjustment
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/products", tags=["Product & Inventory Management"])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    if db.query(Product).filter(Product.sku == product_data.sku.strip()).first():
        raise HTTPException(status_code=409, detail="Product code already exists")
    product = Product(
        sku=product_data.sku.strip(), name=product_data.name.strip(),
        description=product_data.description, category=product_data.category.strip(),
        price=product_data.price, stock_quantity=product_data.stock_quantity, is_active=True
    )
    try:
        db.add(product)
        db.flush()
        if product.stock_quantity:
            db.add(StockMovement(
                product_id=product.id, order_id=None, performed_by=current_user.id,
                movement_type="in", quantity=product.stock_quantity, stock_before=0,
                stock_after=product.stock_quantity, reason="Opening stock when product was created"
            ))
        db.commit()
        db.refresh(product)
        return product
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create product")


@router.get("/", response_model=list[ProductResponse])
def get_products(
    search: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=100),
    status_filter: str = Query(default="active", alias="status", pattern="^(active|inactive|all)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    query = db.query(Product)
    if current_user.role != "admin":
        query = query.filter(Product.is_active.is_(True))
    elif status_filter == "active":
        query = query.filter(Product.is_active.is_(True))
    elif status_filter == "inactive":
        query = query.filter(Product.is_active.is_(False))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Product.sku.ilike(term), Product.name.ilike(term)))
    if category:
        query = query.filter(Product.category.ilike(f"%{category.strip()}%"))
    return query.order_by(Product.id.desc()).offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(Product).filter(Product.id == product_id)
    if current_user.role != "admin":
        query = query.filter(Product.is_active.is_(True))
    product = query.first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    values = product_data.model_dump(exclude_unset=True)
    if "sku" in values and values["sku"] is not None:
        values["sku"] = values["sku"].strip()
        duplicate = db.query(Product).filter(Product.sku == values["sku"], Product.id != product_id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Product code already exists")
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
    if "category" in values and values["category"] is not None:
        values["category"] = values["category"].strip()
    for key, value in values.items():
        setattr(product, key, value)
    try:
        db.commit()
        db.refresh(product)
        return product
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update product")


@router.post("/{product_id}/stock", response_model=ProductResponse)
def adjust_stock(product_id: int, adjustment: StockAdjustment, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    try:
        product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).with_for_update().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        before = product.stock_quantity
        if adjustment.movement_type == "in":
            product.stock_quantity += adjustment.quantity
        else:
            if adjustment.quantity > before:
                raise HTTPException(status_code=400, detail="Insufficient stock")
            product.stock_quantity -= adjustment.quantity
        db.add(StockMovement(
            product_id=product.id, order_id=None, performed_by=current_user.id,
            movement_type=adjustment.movement_type, quantity=adjustment.quantity,
            stock_before=before, stock_after=product.stock_quantity, reason=adjustment.reason
        ))
        db.commit()
        db.refresh(product)
        return product
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to adjust product stock")


@router.delete("/{product_id}")
def deactivate_product(product_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    try:
        db.commit()
        return {"message": "Product deactivated successfully"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to deactivate product")
