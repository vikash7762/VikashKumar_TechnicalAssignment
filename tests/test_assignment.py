
from decimal import Decimal

from app.models import Customer, Product, User


def create_customer(db):
    customer = Customer(
        name="Test Customer",
        email="customer@test.com",
        phone="9999999999",
        address="Test City",
        is_active=True
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_product(db, sku="TEST-001", stock=10):
    product = Product(
        sku=sku,
        name="Test Product",
        description="Automated test product",
        category="Testing",
        price=Decimal("100.00"),
        stock_quantity=stock,
        is_active=True
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_order_discount_calculation(client, db):
    customer = create_customer(db)
    product_one = create_product(db, sku="TEST-001", stock=10)
    product_two = Product(
        sku="TEST-002", name="Second Test Product", category="Testing",
        price=Decimal("50.00"), stock_quantity=10, is_active=True
    )
    db.add(product_two)
    db.commit()
    db.refresh(product_two)

    response = client.post(
        "/orders/",
        json={
            "customer_id": customer.id,
            "discount_percentage": 10,
            "items": [
                {"product_id": product_one.id, "quantity": 2},
                {"product_id": product_two.id, "quantity": 1}
            ]
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert Decimal(str(data["subtotal"])) == Decimal("250.00")
    assert Decimal(str(data["discount_amount"])) == Decimal("25.00")
    assert Decimal(str(data["grand_total"])) == Decimal("225.00")
    assert data["status"] == "draft"


def test_order_confirmation_deducts_stock(client, db):
    customer = create_customer(db)
    product = create_product(db, stock=10)

    response = client.post(
        "/orders/",
        json={
            "customer_id": customer.id,
            "discount_percentage": 0,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 3
                }
            ]
        }
    )

    assert response.status_code == 201
    order_id = response.json()["id"]

    confirm_response = client.post(
        f"/orders/{order_id}/confirm"
    )

    assert confirm_response.status_code == 200

    db.refresh(product)
    assert product.stock_quantity == 7


def test_order_cancellation_restores_stock(client, db):
    customer = create_customer(db)
    product = create_product(db, stock=10)

    response = client.post(
        "/orders/",
        json={
            "customer_id": customer.id,
            "discount_percentage": 0,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 4
                }
            ]
        }
    )

    assert response.status_code == 201
    order_id = response.json()["id"]

    confirm_response = client.post(
        f"/orders/{order_id}/confirm"
    )
    assert confirm_response.status_code == 200

    cancel_response = client.post(
        f"/orders/{order_id}/cancel"
    )
    assert cancel_response.status_code == 200

    db.refresh(product)
    assert product.stock_quantity == 10


def test_csv_import_success(client, db):
    csv_content = (
        "product_code,product_name,category,price,stock_quantity,status\n"
        "AUTO-001,Keyboard,Accessories,850.00,10,active\n"
    )

    response = client.post(
        "/import/products",
        files={
            "file": (
                "valid_test.csv",
                csv_content,
                "text/csv"
            )
        }
    )

    assert response.status_code == 200
    assert response.json()["imported_count"] == 1

    product = db.query(Product).filter(
        Product.sku == "AUTO-001"
    ).first()

    assert product is not None
    assert product.stock_quantity == 10


def test_csv_import_rejects_negative_price(client, db):
    csv_content = (
        "product_code,product_name,category,price,stock_quantity,status\n"
        "AUTO-002,Mouse,Accessories,450.00,10,active\n"
        "AUTO-003,Invalid Mouse,Accessories,-100.00,5,active\n"
    )

    response = client.post(
        "/import/products",
        files={
            "file": (
                "invalid_test.csv",
                csv_content,
                "text/csv"
            )
        }
    )

    assert response.status_code == 400

    product = db.query(Product).filter(
        Product.sku == "AUTO-002"
    ).first()

    assert product is None


def test_csv_import_requires_admin(client, db):
    from app.dependencies import get_current_user
    from app.main import app

    sales_user = User(
        name="Test Sales User",
        email="sales@test.com",
        password_hash="test-hash",
        role="sales_user",
        is_active=True
    )

    db.add(sales_user)
    db.commit()
    db.refresh(sales_user)

    app.dependency_overrides[get_current_user] = lambda: sales_user

    response = client.post(
        "/import/products",
        files={
            "file": (
                "test.csv",
                "product_code,product_name,category,price,stock_quantity,status\n"
                "AUTO-004,Mouse,Accessories,100.00,5,active\n",
                "text/csv"
            )
        }
    )

    assert response.status_code == 403



def test_order_rejects_zero_quantity(client, db):
    customer = create_customer(db)
    product = create_product(db)
    response = client.post("/orders/", json={"customer_id": customer.id, "items": [{"product_id": product.id, "quantity": 0}]})
    assert response.status_code == 422


def test_order_rejects_negative_quantity(client, db):
    customer = create_customer(db)
    product = create_product(db)
    response = client.post("/orders/", json={"customer_id": customer.id, "items": [{"product_id": product.id, "quantity": -1}]})
    assert response.status_code == 422


def test_order_rejects_discount_above_twenty_percent(client, db):
    customer = create_customer(db)
    product = create_product(db)
    response = client.post("/orders/", json={"customer_id": customer.id, "discount_percentage": 20.01, "items": [{"product_id": product.id, "quantity": 1}]})
    assert response.status_code == 422


def test_insufficient_stock_confirmation_is_atomic(client, db):
    customer = create_customer(db)
    product = create_product(db, stock=2)
    response = client.post("/orders/", json={"customer_id": customer.id, "items": [{"product_id": product.id, "quantity": 3}]})
    order_id = response.json()["id"]
    confirm = client.post(f"/orders/{order_id}/confirm")
    assert confirm.status_code == 400
    db.refresh(product)
    assert product.stock_quantity == 2
    assert client.get(f"/orders/{order_id}").json()["status"] == "draft"


def test_repeated_confirmation_does_not_deduct_twice(client, db):
    customer = create_customer(db)
    product = create_product(db, stock=8)
    response = client.post("/orders/", json={"customer_id": customer.id, "items": [{"product_id": product.id, "quantity": 3}]})
    order_id = response.json()["id"]
    assert client.post(f"/orders/{order_id}/confirm").status_code == 200
    assert client.post(f"/orders/{order_id}/confirm").status_code == 400
    db.refresh(product)
    assert product.stock_quantity == 5


def test_repeated_cancellation_does_not_restore_twice(client, db):
    customer = create_customer(db)
    product = create_product(db, stock=8)
    response = client.post("/orders/", json={"customer_id": customer.id, "items": [{"product_id": product.id, "quantity": 3}]})
    order_id = response.json()["id"]
    assert client.post(f"/orders/{order_id}/confirm").status_code == 200
    assert client.post(f"/orders/{order_id}/cancel").status_code == 200
    assert client.post(f"/orders/{order_id}/cancel").status_code == 400
    db.refresh(product)
    assert product.stock_quantity == 8


def test_draft_cancellation_does_not_change_stock(client, db):
    customer = create_customer(db)
    product = create_product(db, stock=8)
    response = client.post("/orders/", json={"customer_id": customer.id, "items": [{"product_id": product.id, "quantity": 3}]})
    order_id = response.json()["id"]
    assert client.post(f"/orders/{order_id}/cancel").status_code == 200
    db.refresh(product)
    assert product.stock_quantity == 8


def test_sales_user_cannot_view_another_users_order(client, db):
    from app.dependencies import get_current_user
    from app.main import app
    customer = create_customer(db)
    product = create_product(db)
    order = client.post("/orders/", json={"customer_id": customer.id, "items": [{"product_id": product.id, "quantity": 1}]}).json()
    sales_user = User(name="Sales User", email="sales2@test.com", password_hash="test-hash", role="sales_user", is_active=True)
    db.add(sales_user)
    db.commit()
    db.refresh(sales_user)
    app.dependency_overrides[get_current_user] = lambda: sales_user
    try:
        assert client.get(f"/orders/{order['id']}").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_stock_adjustment_requires_reason(client, db):
    product = create_product(db)
    response = client.post(f"/products/{product.id}/stock", json={"movement_type": "in", "quantity": 2})
    assert response.status_code == 422


def test_debugging_calculate_total_accumulates_all_items():
    from app.debugging_exercise import calculate_total
    assert calculate_total([{"quantity": 2, "rate": "100"}, {"quantity": 3, "rate": "50"}]) == Decimal("350.00")
    assert calculate_total([]) == Decimal("0.00")


def test_debugging_calculate_total_rejects_missing_or_invalid_values():
    from app.debugging_exercise import calculate_total
    import pytest
    with pytest.raises(ValueError):
        calculate_total([{"quantity": 1}])
    with pytest.raises(ValueError):
        calculate_total([{"quantity": 0, "rate": 10}])
    with pytest.raises(ValueError):
        calculate_total([{"quantity": 1, "rate": -1}])
