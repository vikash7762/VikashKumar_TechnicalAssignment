from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Any


def calculate_total(items: Iterable[Mapping[str, Any]]) -> Decimal:
    """Return the sum of quantity * rate for each item.

    Each item must provide a positive integer `quantity` and a non-negative
    finite decimal-compatible `rate`. Empty input correctly returns 0.00.
    """
    total = Decimal("0.00")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            raise ValueError(f"Item {index} must be an object containing quantity and rate")
        if "quantity" not in item or "rate" not in item:
            raise ValueError(f"Item {index} must contain quantity and rate")
        quantity = item["quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError(f"Item {index} quantity must be a positive integer")
        try:
            rate = Decimal(str(item["rate"]))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(f"Item {index} rate must be a valid number")
        if not rate.is_finite() or rate < 0:
            raise ValueError(f"Item {index} rate must be a finite non-negative number")
        total += rate * quantity
    return total.quantize(Decimal("0.01"))
