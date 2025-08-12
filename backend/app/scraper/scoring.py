from __future__ import annotations

from datetime import datetime, timezone


def score_post(*, published_at: datetime | None, content_length: int | None, source_weight: float = 1.0) -> float:
    """Compute a 0-100 score favoring recent, substantial content.

    - Recency: exponential decay over 365 days
    - Length: logarithmic benefit up to ~4k chars
    - Source weight: multiplier for trusted sources (e.g., official blog > social repost)
    """
    now = datetime.now(timezone.utc)

    # Recency component (0..1)
    if published_at is None:
        recency = 0.3  # unknown date still gets a small baseline
    else:
        days = max((now - published_at).days, 0)
        half_life_days = 90
        recency = 2 ** (-(days / half_life_days))  # half every 90 days

    # Length component (0..1)
    n = max(content_length or 0, 0)
    length = min((n / 4000.0), 1.0) if n < 4000 else 1.0
    base = 0.6 * recency + 0.4 * length
    return round(max(0.0, min(100.0, 100.0 * base * source_weight)), 2)
