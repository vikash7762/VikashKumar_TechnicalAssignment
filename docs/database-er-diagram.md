
# Sales Order & Inventory Management System

## Database ER Diagram

```mermaid
erDiagram
    USERS ||--o{ SALES_ORDERS : creates
    CUSTOMERS ||--o{ SALES_ORDERS : places
    SALES_ORDERS ||--|{ SALES_ORDER_ITEMS : contains
    PRODUCTS ||--o{ SALES_ORDER_ITEMS : included_in
    PRODUCTS ||--o{ STOCK_MOVEMENTS : records
    SALES_ORDERS ||--o{ STOCK_MOVEMENTS : generates
    USERS ||--o{ STOCK_MOVEMENTS : performs

    USERS {
        int id PK
        string name
        string email UK
        string password_hash
        string role
        boolean is_active
    }

    CUSTOMERS {
        int id PK
        string name
        string email
        string phone
        string address
    }

    PRODUCTS {
        int id PK
        string sku UK
        string name
        decimal price
        int stock_quantity
    }

    SALES_ORDERS {
        int id PK
        string order_number UK
        int customer_id FK
        int created_by FK
        decimal total_amount
        string status
        datetime created_at
    }

    SALES_ORDER_ITEMS {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal unit_price
        decimal line_total
    }

    STOCK_MOVEMENTS {
        int id PK
        int product_id FK
        int order_id FK
        int performed_by FK
        string movement_type
        int quantity
        int stock_before
        int stock_after
    }
```


## Additional fields

- `products.category` stores the product category used by catalogue filters and CSV imports.
- `stock_movements.reason` stores the explanation for each inventory movement. New manual stock adjustments require a reason; system-generated order and opening-stock movements also record their cause.
