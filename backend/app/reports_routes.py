from datetime import date, datetime, time
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case

from app.database import get_db
from app.models import SalesOrder, SalesOrderItem, Product, Customer, StockMovement, User
from app.dependencies import require_role

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


def _date_filters(query, model, date_from, date_to):
    if date_from:
        query = query.filter(model.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(model.created_at <= datetime.combine(date_to, time.max))
    return query


@router.get("/sales-summary")
def get_sales_summary(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    count, total = db.query(func.count(SalesOrder.id), func.coalesce(func.sum(SalesOrder.grand_total), 0)).filter(SalesOrder.status == "confirmed").first()
    return {"total_confirmed_orders": count, "total_sales": total}


@router.get("/inventory-summary")
def get_inventory_summary(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    count, units, value = db.query(func.count(Product.id), func.coalesce(func.sum(Product.stock_quantity), 0), func.coalesce(func.sum(Product.price * Product.stock_quantity), 0)).filter(Product.is_active.is_(True)).first()
    return {"total_active_products": count, "total_stock_units": units, "total_inventory_value": value}


@router.get("/order-status")
def get_order_status_report(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    results = db.query(SalesOrder.status, func.count(SalesOrder.id)).group_by(SalesOrder.status).all()
    report = {"draft": 0, "confirmed": 0, "cancelled": 0}
    for status_name, count in results:
        report[status_name] = count
    return report


@router.get("/customer-sales-summary")
def customer_sales_summary(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    # Aggregate orders before joining customers: prevents duplicate totals from item-level joins.
    orders = db.query(
        SalesOrder.customer_id.label("customer_id"),
        func.count(SalesOrder.id).label("confirmed_order_count"),
        func.coalesce(func.sum(SalesOrder.grand_total), 0).label("total_sales")
    ).filter(SalesOrder.status == "confirmed")
    if date_from:
        orders = orders.filter(SalesOrder.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        orders = orders.filter(SalesOrder.created_at <= datetime.combine(date_to, time.max))
    orders = orders.group_by(SalesOrder.customer_id).subquery()
    rows = db.query(
        Customer.id.label("customer_id"), Customer.name.label("customer_name"),
        func.coalesce(orders.c.confirmed_order_count, 0).label("confirmed_order_count"),
        func.coalesce(orders.c.total_sales, 0).label("total_sales")
    ).outerjoin(orders, orders.c.customer_id == Customer.id).order_by(Customer.name).all()
    return [{"customer_id": r.customer_id, "customer_name": r.customer_name, "confirmed_order_count": r.confirmed_order_count, "total_sales": r.total_sales} for r in rows]


@router.get("/product-sales-summary")
def product_sales_summary(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    # Aggregate confirmed order items first, then outer join so products with no sales appear as zero.
    item_totals = db.query(
        SalesOrderItem.product_id.label("product_id"),
        func.sum(SalesOrderItem.quantity).label("quantity_sold"),
        func.sum(SalesOrderItem.line_total).label("gross_item_value")
    ).join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id).filter(SalesOrder.status == "confirmed")
    if date_from:
        item_totals = item_totals.filter(SalesOrder.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        item_totals = item_totals.filter(SalesOrder.created_at <= datetime.combine(date_to, time.max))
    item_totals = item_totals.group_by(SalesOrderItem.product_id).subquery()
    rows = db.query(
        Product.id.label("product_id"), Product.sku.label("product_code"), Product.name.label("product_name"),
        func.coalesce(item_totals.c.quantity_sold, 0).label("quantity_sold"),
        func.coalesce(item_totals.c.gross_item_value, 0).label("gross_item_value")
    ).outerjoin(item_totals, item_totals.c.product_id == Product.id).order_by(Product.name).all()
    return [{"product_id": r.product_id, "product_code": r.product_code, "product_name": r.product_name,
             "quantity_sold": r.quantity_sold, "gross_item_value": r.gross_item_value} for r in rows]


@router.get("/low-stock")
def low_stock_report(threshold: int = Query(default=10, ge=0), db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    products = db.query(Product).filter(Product.is_active.is_(True), Product.stock_quantity < threshold).order_by(Product.stock_quantity.asc()).all()
    return [{"product_id": p.id, "product_code": p.sku, "product_name": p.name, "stock_quantity": p.stock_quantity, "threshold": threshold} for p in products]


@router.get("/stock-movements")
def stock_movement_history(product_id: int | None = None, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    query = db.query(StockMovement, Product, User).join(Product, Product.id == StockMovement.product_id).join(User, User.id == StockMovement.performed_by)
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    rows = query.order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).limit(1000).all()
    return [{"movement_id": m.id, "product_id": p.id, "product_code": p.sku, "product_name": p.name,
             "movement_type": m.movement_type, "quantity": m.quantity, "stock_before": m.stock_before,
             "stock_after": m.stock_after, "order_id": m.order_id, "reason": m.reason,
             "performed_by": u.name, "created_at": m.created_at} for m, p, u in rows]
