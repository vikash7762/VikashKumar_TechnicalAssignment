# Test Cases and Verification Checklist

Run automated tests from the project root with `PYTHONPATH=backend python -m pytest tests -v`.

| ID | Scenario | Automated coverage | Expected result |
|---|---|---|---|
| TC-01 | Multi-item order with 10% discount | `test_order_discount_calculation` (single-item calculation; add multi-item extension in local DB test) | Backend calculates subtotal, discount and grand total |
| TC-02 | Quantity is zero | `test_order_rejects_zero_quantity` | HTTP 422; no order created |
| TC-03 | Quantity is negative | `test_order_rejects_negative_quantity` | HTTP 422; no order created |
| TC-04 | Discount exceeds 20% | `test_order_rejects_discount_above_twenty_percent` | HTTP 422; no order created |
| TC-05 | Confirm with sufficient stock | `test_order_confirmation_deducts_stock` | Stock decreases once and order is confirmed |
| TC-06 | Insufficient stock on one item | `test_insufficient_stock_confirmation_is_atomic` | HTTP 400; no stock/status changes |
| TC-07 | Confirm same order twice | `test_repeated_confirmation_does_not_deduct_twice` | Second confirmation rejected; no second deduction |
| TC-08 | Cancel confirmed order | `test_order_cancellation_restores_stock` | Stock restored once |
| TC-09 | Cancel same order twice | `test_repeated_cancellation_does_not_restore_twice` | Second cancellation rejected; no second restoration |
| TC-10 | Cancel draft order | `test_draft_cancellation_does_not_change_stock` | Status cancelled; inventory unchanged |
| TC-11 | Sales User accesses another user's order | `test_sales_user_cannot_view_another_users_order` | HTTP 403 |
| TC-12 | CSV valid file | `test_csv_import_success` | Rows imported and opening stock movement recorded |
| TC-13 | CSV invalid price / all-or-nothing | `test_csv_import_rejects_negative_price` | HTTP 400; no rows imported |
| TC-14 | CSV endpoint role restriction | `test_csv_import_requires_admin` | HTTP 403 for Sales User |
| TC-15 | Stock adjustment without reason | `test_stock_adjustment_requires_reason` | HTTP 422 |
| TC-16 | Debugging total accumulation | `test_debugging_calculate_total_accumulates_all_items` | Expected result 350.00; empty list returns 0.00 |
| TC-17 | Debugging invalid inputs | `test_debugging_calculate_total_rejects_missing_or_invalid_values` | Missing fields, zero quantity and negative rate rejected |

## Manual checks still required on the target computer

- Admin and Sales User login and page navigation.
- Admin-only customer/product create, update, deactivate and stock adjustment.
- Sales User cannot create/update/deactivate master data through direct API calls.
- Product search by code/name, category filter and active/inactive status filter.
- Customer search and active/inactive status filter.
- Swagger checks for all report endpoints and their date/threshold parameters.
- Execute the migration against the existing MySQL database and verify existing rows remain intact.
- Record the 5–8 minute demonstration video.

Do not mark a manual test as passed until it has actually been run against the local MySQL application.
