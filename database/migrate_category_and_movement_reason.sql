USE sales_inventory_db;

-- Safe/idempotent MySQL migration: adds only columns that do not already exist.
SET @has_category = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'category'
);
SET @sql_category = IF(@has_category = 0,
  'ALTER TABLE products ADD COLUMN category VARCHAR(100) NOT NULL DEFAULT ''General'' AFTER description',
  'SELECT ''products.category already exists'' AS migration_status');
PREPARE stmt_category FROM @sql_category;
EXECUTE stmt_category;
DEALLOCATE PREPARE stmt_category;

SET @has_reason = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'stock_movements' AND COLUMN_NAME = 'reason'
);
SET @sql_reason = IF(@has_reason = 0,
  'ALTER TABLE stock_movements ADD COLUMN reason VARCHAR(255) NOT NULL DEFAULT ''Legacy record'' AFTER stock_after',
  'SELECT ''stock_movements.reason already exists'' AS migration_status');
PREPARE stmt_reason FROM @sql_reason;
EXECUTE stmt_reason;
DEALLOCATE PREPARE stmt_reason;
