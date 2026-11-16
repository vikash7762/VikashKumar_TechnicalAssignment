
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import Customer
from app.schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse
)
from app.dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/customers",
    tags=["Customer Management"]
)


# =====================================
# ADD NEW CUSTOMER (ADMIN ONLY)
# =====================================

@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED
)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    new_customer = Customer(
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone,
        address=customer_data.address,
        is_active=True
    )

    try:
        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        return new_customer

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create customer"
        )


# =====================================
# VIEW ALL ACTIVE CUSTOMERS
# (ADMIN AND SALES USER)
# =====================================

@router.get(
    "/",
    response_model=list[CustomerResponse]
)
def get_customers(
    search: str | None = Query(default=None, max_length=100),
    status_filter: str = Query(default="active", alias="status", pattern="^(active|inactive|all)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(Customer)
    if current_user.role != "admin":
        query = query.filter(Customer.is_active.is_(True))
    elif status_filter == "active":
        query = query.filter(Customer.is_active.is_(True))
    elif status_filter == "inactive":
        query = query.filter(Customer.is_active.is_(False))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Customer.name.ilike(term), Customer.email.ilike(term), Customer.phone.ilike(term)))
    return query.order_by(Customer.id.desc()).all()


# =====================================
# VIEW CUSTOMER BY ID
# (ADMIN AND SALES USER)
# =====================================

@router.get(
    "/{customer_id}",
    response_model=CustomerResponse
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.is_active == True
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer


# =====================================
# UPDATE CUSTOMER (ADMIN ONLY)
# =====================================

@router.put(
    "/{customer_id}",
    response_model=CustomerResponse
)
def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.is_active == True
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    update_data = customer_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(customer, key, value)

    try:
        db.commit()
        db.refresh(customer)
        return customer

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update customer"
        )


# =====================================
# DEACTIVATE CUSTOMER (ADMIN ONLY)
# =====================================

@router.delete(
    "/{customer_id}"
)
def deactivate_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.is_active == True
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    try:
        customer.is_active = False
        db.commit()

        return {
            "message": "Customer deactivated successfully"
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to deactivate customer"
        )
