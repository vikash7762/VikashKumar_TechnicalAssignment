# Debugging Exercise – `calculate_total`

## Bug

The original implementation overwrote the running total for every item instead of accumulating each item's amount. In effect, it returned only the last line amount when more than one item was supplied.

## Corrected implementation

The corrected function is in `backend/app/debugging_exercise.py`. It initializes a `Decimal("0.00")` accumulator and adds `quantity * rate` for every item. It validates that each row has both fields, quantity is a positive integer, and rate is a finite non-negative number. An empty list returns `0.00`.

## Expected example

```python
items = [
    {"quantity": 2, "rate": "100.00"},
    {"quantity": 3, "rate": "50.00"},
]
# 2 * 100 + 3 * 50 = 350.00
```

Expected result: `350.00`.

## Automated verification

The tests `test_debugging_calculate_total_accumulates_all_items` and `test_debugging_calculate_total_rejects_missing_or_invalid_values` cover the required total, empty input, missing values, zero quantity and negative rate.
