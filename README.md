# Sales Order & Inventory Management System

A role-based Sales Order and Inventory Management System built for the Savyant Systems technical assignment using FastAPI, Python, SQLAlchemy, MySQL, HTML, CSS and JavaScript.

## Technology

- Python 3.10+
- FastAPI and Uvicorn
- MySQL 8+ with InnoDB
- SQLAlchemy 2.x and PyMySQL
- Pydantic v2
- JWT authentication and Argon2 password hashing
- HTML, CSS and vanilla JavaScript
- Pytest and FastAPI TestClient

## Project structure

```text
Sales-Inventory-System/
├── backend/
│   ├── app/                 # API routes, models, schemas, auth and DB
│   ├── create_admin.py      # Interactive admin account creation
│   └── .env.example
├── database/
│   ├── schema.sql           # Fresh database schema
│   └── migrate_category_and_movement_reason.sql
├── docs/
│   ├── database-er-diagram.md
│   ├── schema.sql
│   ├── database-migration.md
│   ├── report_queries.sql   # Five required standalone SQL exercises
│   ├── valid_products.csv
│   ├── invalid_products.csv
│   ├── test-cases.md
│   └── debugging_exercise.md
├── frontend/                # login, dashboard, customers, products, orders
├── tests/                   # automated tests and fixtures
├── AI_USAGE.md
├── requirements.txt
└── README.md
```

## Setup

1. Install Python 3.10+ and MySQL 8+.
2. Create a virtual environment from the project root:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Create the database and tables. In MySQL Workbench, open and execute `database/schema.sql`.
4. Copy `backend/.env.example` to `backend/.env` and set your local database username, password, database name and a long random `SECRET_KEY`. Never commit `.env`.
5. Create the Admin account interactively:

   ```powershell
   cd backend
   python create_admin.py
   ```

   The script asks for the admin name, email and password; no default credentials are stored in the repository.
6. Start the API from the `backend` directory:

   ```powershell
   uvicorn app.main:app --reload
   ```

7. Open `http://127.0.0.1:8000/docs` for interactive API documentation. Serve the `frontend` directory using VS Code Live Server and open `frontend/login.html`.
8. Sales User accounts can be registered using the registration option on the login page. New registrations receive the `sales_user` role.

## Existing database migration

If the database was created before product categories and stock movement reasons were added, do **not** drop or recreate it. Run `database/migrate_category_and_movement_reason.sql` once in MySQL Workbench. It adds `products.category` and `stock_movements.reason` only when missing and preserves existing records. Existing rows receive `General` and `Legacy record` defaults. See `docs/database-migration.md`.

## Roles and permissions

- **Admin:** manages customers, products, stock, imports, all orders and reports.
- **Sales User:** views active customers/products and creates, views, confirms and cancels only their own orders.
- Master data writes, stock adjustments, CSV imports and reports are Admin-only. The backend enforces permissions independently of frontend visibility.

## Order and inventory rules

- Orders are created as drafts. Draft creation does not reserve or deduct stock.
- Each order item stores the product's current price as `unit_price`, preserving historical pricing.
- The backend calculates subtotal, discount and grand total using `Decimal`; discounts are limited to 0–20%.
- Confirmation locks the order and product rows (`SELECT ... FOR UPDATE` through SQLAlchemy), validates every item's stock before changing any product, then updates stock, movement history and order status in one database transaction. Products are locked in sorted ID order to reduce deadlock risk.
- Cancelling a draft changes only its status. Cancelling a confirmed order restores stock exactly once and records inbound movements in the same transaction.
- Products/customers referenced by orders are deactivated rather than hard-deleted.
- Admin stock adjustments require a reason; all stock movements retain before/after quantities and a reason.

## CSV import

Admin-only endpoint: `POST /import/products` (multipart field name `file`). The CSV header must be exactly:

```csv
product_code,product_name,category,price,stock_quantity,status
```

Status must be `active` or `inactive`. Duplicate product codes, missing required values, invalid prices, negative stock, invalid status, and duplicate codes in the file are rejected. The importer validates all rows before inserting any product. Opening stock is recorded in `stock_movements`. Sample files are in `docs/valid_products.csv` and `docs/invalid_products.csv`.

## Reports

Admin-only endpoints:

- `GET /reports/customer-sales-summary?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- `GET /reports/product-sales-summary?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- `GET /reports/low-stock?threshold=10`
- `GET /reports/stock-movements`
- `GET /reports/sales-summary`
- `GET /reports/inventory-summary`
- `GET /reports/order-status`

The customer report aggregates orders before joining customers, includes customers with zero confirmed orders, and avoids multiplying order totals by item rows. Product sales use confirmed order items and gross line value before order-level discounts. The five required SQL exercise queries are in `docs/report_queries.sql`.

## API examples

Create an order (authenticated):

```http
POST /orders/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "customer_id": 1,
  "discount_percentage": 10,
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 2, "quantity": 1}
  ]
}
```

Adjust stock (Admin only):

```http
POST /products/1/stock
Content-Type: application/json
Authorization: Bearer <admin_access_token>

{"movement_type": "in", "quantity": 5, "reason": "Received supplier delivery"}
```

Product search and filtering:

```http
GET /products/?search=keyboard&category=Accessories&status=active&skip=0&limit=100
```

## Automated tests

From the project root, activate the virtual environment and run:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest tests -v
```

Tests use an in-memory SQLite database through dependency overrides. The production application uses MySQL. Run the tests after installing all dependencies from `requirements.txt`.

## Assumptions and limitations

- Currency is INR (₹); prices are stored as fixed-point decimals with two fractional digits.
- CSV product codes map to the database `products.sku` field.
- CSV status accepts `active` or `inactive`.
- The application is intended for a local technical-assignment demonstration; production deployment would additionally require HTTPS, managed secrets, stronger operational logging, backups and deployment hardening.
- The browser frontend is served separately from FastAPI during local development; CORS permits the configured localhost Live Server origins.

## AI usage

AI assistance and review practices are disclosed in `AI_USAGE.md`.
