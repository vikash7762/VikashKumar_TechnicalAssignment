
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import uuid

from app.database import get_db
from app.models import (
    SalesOrder,
    SalesOrderItem,
    Customer,
    Product,
    StockMovement
)
from app.schemas import (
    SalesOrderCreate,
    SalesOrderResponse
)
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/orders",
    tags=["Sales Order Management"]
)


def money(value: Decimal) -> Decimal:
    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# =====================================
# CREATE SALES ORDER (DRAFT)
# =====================================

@router.post(
    "/",
    response_model=SalesOrderResponse,
    status_code=status.HTTP_201_CREATED
)
def create_sales_order(
    order_data: SalesOrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.id == order_data.customer_id,
        Customer.is_active == True
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found or inactive"
        )

    product_ids = [item.product_id for item in order_data.items]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate products are not allowed in one order"
        )

    try:
        subtotal = Decimal("0.00")

        discount_percentage = Decimal(
            str(order_data.discount_percentage)
        )

        order_number = (
            f"SO-{datetime.now().strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:8].upper()}"
        )

        new_order = SalesOrder(
            order_number=order_number,
            customer_id=customer.id,
            created_by=current_user.id,
            subtotal=Decimal("0.00"),
            discount_percentage=discount_percentage,
            discount_amount=Decimal("0.00"),
            grand_total=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            status="draft"
        )

        db.add(new_order)
        db.flush()

        for item in order_data.items:

            product = db.query(Product).filter(
                Product.id == item.product_id,
                Product.is_active == True
            ).first()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product ID {item.product_id} not found or inactive"
                )

            unit_price = Decimal(str(product.price))

            line_total = money(
                unit_price * item.quantity
            )

            order_item = SalesOrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=unit_price,
                line_total=line_total
            )

            db.add(order_item)
            subtotal += line_total

        subtotal = money(subtotal)

        discount_amount = money(
            subtotal * discount_percentage / Decimal("100")
        )

        grand_total = money(
            subtotal - discount_amount
        )

        new_order.subtotal = subtotal
        new_order.discount_percentage = discount_percentage
        new_order.discount_amount = discount_amount
        new_order.grand_total = grand_total
        new_order.total_amount = grand_total

        db.commit()
        db.refresh(new_order)

        return new_order

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create sales order"
        )


# =====================================
# CONFIRM SALES ORDER
# =====================================

@router.post(
    "/{order_id}/confirm",
    response_model=SalesOrderResponse
)
def confirm_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        order = db.query(SalesOrder).filter(
            SalesOrder.id == order_id
        ).with_for_update().first()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Sales order not found"
            )

        if (
            current_user.role != "admin"
            and order.created_by != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You cannot confirm another user's order"
            )

        if order.status != "draft":
            raise HTTPException(
                status_code=400,
                detail="Only draft orders can be confirmed"
            )

        order_items = db.query(SalesOrderItem).filter(
            SalesOrderItem.order_id == order.id
        ).all()

        if not order_items:
            raise HTTPException(
                status_code=400,
                detail="Cannot confirm an empty order"
            )

        product_ids = sorted({
            item.product_id for item in order_items
        })

        products = {}

        for product_id in product_ids:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.is_active == True
            ).with_for_update().first()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product ID {product_id} not found or inactive"
                )

            products[product_id] = product

        for item in order_items:
            product = products[item.product_id]

            if product.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product: {product.name}"
                )

        for item in order_items:
            product = products[item.product_id]

            stock_before = product.stock_quantity
            product.stock_quantity -= item.quantity

            movement = StockMovement(
                product_id=product.id,
                order_id=order.id,
                performed_by=current_user.id,
                movement_type="out",
                quantity=item.quantity,
                stock_before=stock_before,
                stock_after=product.stock_quantity,
                reason=f"Stock deducted for confirmed order {order.order_number}"
            )

            db.add(movement)

        order.status = "confirmed"
        order.confirmed_at = datetime.now()

        db.commit()
        db.refresh(order)

        return order

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to confirm sales order"
        )


# =====================================
# CANCEL SALES ORDER
# =====================================

@router.post(
    "/{order_id}/cancel",
    response_model=SalesOrderResponse
)
def cancel_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        order = db.query(SalesOrder).filter(
            SalesOrder.id == order_id
        ).with_for_update().first()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Sales order not found"
            )

        if (
            current_user.role != "admin"
            and order.created_by != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You cannot cancel another user's order"
            )

        if order.status == "cancelled":
            raise HTTPException(status_code=400, detail="Order is already cancelled")

        if order.status == "confirmed":
            order_items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
            product_ids = sorted({item.product_id for item in order_items})
            products = {}
            for product_id in product_ids:
                product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
                if not product:
                    raise HTTPException(status_code=404, detail=f"Product ID {product_id} not found")
                products[product_id] = product
            for item in order_items:
                product = products[item.product_id]
                stock_before = product.stock_quantity
                product.stock_quantity += item.quantity
                db.add(StockMovement(
                    product_id=product.id, order_id=order.id, performed_by=current_user.id,
                    movement_type="in", quantity=item.quantity, stock_before=stock_before,
                    stock_after=product.stock_quantity,
                    reason=f"Stock restored because order {order.order_number} was cancelled"
                ))
        elif order.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft or confirmed orders can be cancelled")

        # Draft cancellation has no inventory effect because draft orders never reserve stock.
        order.status = "cancelled"
        order.cancelled_at = datetime.now()

        db.commit()
        db.refresh(order)

        return order

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to cancel sales order"
        )


# =====================================
# GET ALL ORDERS
# =====================================

@router.get(
    "/",
    response_model=list[SalesOrderResponse]
)
def get_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(SalesOrder)

    if current_user.role != "admin":
        query = query.filter(
            SalesOrder.created_by == current_user.id
        )

    return query.order_by(
        SalesOrder.id.desc()
    ).all()


# =====================================
# GET ORDER BY ID
# =====================================

@router.get(
    "/{order_id}",
    response_model=SalesOrderResponse
)
def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Sales order not found"
        )

    if (
        current_user.role != "admin"
        and order.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot view another user's order"
        )

    return order
