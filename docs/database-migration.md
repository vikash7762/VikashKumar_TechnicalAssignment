# Database migration: product category and stock movement reason

The application now stores a category for every product and a reason for every stock movement. Existing records are preserved.

From MySQL Workbench or the MySQL command line, select the `sales_inventory_db` connection and run:

```sql
SOURCE C:/path/to/Sales-Inventory-System/database/migrate_category_and_movement_reason.sql;
```

Replace the path with the actual location of the project. Alternatively, open `database/migrate_category_and_movement_reason.sql` in MySQL Workbench and execute the script.

The migration is safe to run more than once. Existing products receive category `General`; existing stock movements receive reason `Legacy record`. New application-generated stock movements require a meaningful reason.

After migration, verify:

```sql
SHOW COLUMNS FROM products LIKE 'category';
SHOW COLUMNS FROM stock_movements LIKE 'reason';
```
