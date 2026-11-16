import csv
import io
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, StockMovement
from app.dependencies import require_role

router = APIRouter(prefix="/import", tags=["CSV Import"])
REQUIRED_COLUMNS = ["product_code", "product_name", "category", "price", "stock_quantity", "status"]


@router.post("/products")
def import_products_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    try:
        raw = file.file.read()
        if len(raw) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="CSV file must be 5 MB or smaller")
        content = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        if reader.fieldnames != REQUIRED_COLUMNS:
            raise HTTPException(status_code=400, detail={
                "message": "CSV columns must match the required format and order",
                "required_columns": REQUIRED_COLUMNS,
                "received_columns": reader.fieldnames or []
            })
        rows = list(reader)
        if not rows:
            raise HTTPException(status_code=400, detail="CSV file contains no product rows")

        errors, parsed, seen = [], [], set()
        for row_number, row in enumerate(rows, start=2):
            if None in row:
                errors.append({"row": row_number, "reason": "Row contains more values than the required six columns"})
            code = (row.get("product_code") or "").strip()
            name = (row.get("product_name") or "").strip()
            category = (row.get("category") or "").strip()
            status_value = (row.get("status") or "").strip().lower()
            try:
                price = Decimal((row.get("price") or "").strip())
                stock = int((row.get("stock_quantity") or "").strip())
            except (InvalidOperation, ValueError):
                errors.append({"row": row_number, "reason": "Price must be a valid decimal and stock_quantity must be a whole number"})
                continue
            if not code or not name or not category:
                errors.append({"row": row_number, "reason": "product_code, product_name and category are required"})
            if code in seen:
                errors.append({"row": row_number, "reason": f"Duplicate product_code in CSV: {code}"})
            seen.add(code)
            if not price.is_finite() or price < 0 or price > Decimal("99999999.99") or max(0, -price.as_tuple().exponent) > 2:
                errors.append({"row": row_number, "reason": "Price must be a non-negative amount with at most two decimal places and fit DECIMAL(10,2)"})
            if stock < 0:
                errors.append({"row": row_number, "reason": "Stock quantity cannot be negative"})
            if status_value not in {"active", "inactive"}:
                errors.append({"row": row_number, "reason": "Status must be active or inactive"})
            if code:
                existing = db.query(Product.id).filter(Product.sku == code).first()
                if existing:
                    errors.append({"row": row_number, "reason": f"Product code already exists: {code}"})
            parsed.append((code, name, category, price, stock, status_value == "active"))

        if errors:
            raise HTTPException(status_code=400, detail={"message": "CSV validation failed; no products were imported", "errors": errors})

        for code, name, category, price, stock, active in parsed:
            product = Product(sku=code, name=name, category=category, price=price, stock_quantity=stock, is_active=active)
            db.add(product)
            db.flush()
            if stock > 0:
                db.add(StockMovement(
                    product_id=product.id, order_id=None, performed_by=current_user.id,
                    movement_type="in", quantity=stock, stock_before=0, stock_after=stock,
                    reason="Opening stock imported from CSV"
                ))
        db.commit()
        return {"message": "CSV products imported successfully", "imported_count": len(parsed)}
    except HTTPException:
        db.rollback()
        raise
    except UnicodeDecodeError:
        db.rollback()
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to import CSV products")
