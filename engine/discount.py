def apply_discount(amount: float, threshold: float = 2500.0, discount: float = 100.0) -> float:
    """Return discount amount if bill exceeds threshold, else 0."""
    return discount if amount > threshold else 0.0
