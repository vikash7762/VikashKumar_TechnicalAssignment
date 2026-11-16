from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.auth_routes import router as auth_router
from app.customer_routes import router as customer_router
from app.product_routes import router as product_router

from app.order_routes import router as order_router
from app.reports_routes import router as reports_router
from app.import_routes import router as import_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sales Inventory Management System",
    description="Sales Order and Inventory Management API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register authentication routes
app.include_router(auth_router)

# Register customer routes
app.include_router(customer_router)

# Register product routes
app.include_router(product_router)

app.include_router(order_router)

app.include_router(reports_router)

app.include_router(import_router)


@app.get("/")
def home():
    return {
        "message": "Sales Inventory Management System API is running!"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )