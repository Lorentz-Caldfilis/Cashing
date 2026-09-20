"""Derived category for a new record.

Only the first, most conservative layer of the design philosophy (§4.5) is
implemented here: an identical description the user has already categorised
inherits that category. Anything else stays unknown (``None``) until the
Adaptive Classification Specification exists. No rules, models or network.
"""


def derive_category(description: str, lookup) -> str | None:
    """``lookup(description)`` returns the latest category for that exact text or None."""
    key = description.strip()
    if not key:
        return None
    return lookup(key)
