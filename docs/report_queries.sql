-- Required SQL exercise 1: Top 3 customers by confirmed order grand total.
SELECT c.id, c.name, SUM(so.grand_total) AS confirmed_sales
FROM customers c
JOIN sales_orders so ON so.customer_id = c.id
WHERE so.status = 'confirmed'
GROUP BY c.id, c.name
ORDER BY confirmed_sales DESC
LIMIT 3;

-- Required SQL exercise 2: Top 3 products by confirmed quantity sold.
SELECT p.id, p.sku AS product_code, p.name AS product_name,
       SUM(soi.quantity) AS quantity_sold
FROM products p
JOIN sales_order_items soi ON soi.product_id = p.id
JOIN sales_orders so ON so.id = soi.order_id
WHERE so.status = 'confirmed'
GROUP BY p.id, p.sku, p.name
ORDER BY quantity_sold DESC
LIMIT 3;

-- Required SQL exercise 3: Customers who have never placed any order.
SELECT c.id, c.name, c.email, c.phone
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM sales_orders so WHERE so.customer_id = c.id
)
ORDER BY c.name;

-- Required SQL exercise 4: Month-wise confirmed sales grouped by year and month.
SELECT
    YEAR(so.confirmed_at) AS sales_year,
    MONTH(so.confirmed_at) AS sales_month,
    SUM(so.grand_total) AS confirmed_sales
FROM sales_orders so
WHERE so.status = 'confirmed'
  AND so.confirmed_at IS NOT NULL
GROUP BY
    YEAR(so.confirmed_at),
    MONTH(so.confirmed_at)
ORDER BY sales_year, sales_month;

-- Required SQL exercise 5: Products below a supplied stock threshold.
SET @stock_threshold = 10;
SELECT p.id, p.sku AS product_code, p.name AS product_name, p.stock_quantity
FROM products p
WHERE p.is_active = TRUE AND p.stock_quantity < @stock_threshold
ORDER BY p.stock_quantity ASC, p.name;
