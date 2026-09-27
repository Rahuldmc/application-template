def normalize_email(email: str) -> str:
    """Canonical form used for storage and lookup, so `A@x.com` and `a@x.com` match."""
    return email.strip().lower()
