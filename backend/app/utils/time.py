from datetime import UTC, datetime


def utcnow() -> datetime:
    """Timezone-aware current time in UTC. Never use naive datetimes."""
    return datetime.now(UTC)
