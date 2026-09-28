"""Article deduplication (plan section 17, pipeline step 1).

Collapses re-published wire copy and near-identical headlines about the
same event on the same day to a single stable hash, independent of the
reporting source.
"""

import hashlib
import re
from datetime import datetime

_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9\s]")


def normalize_headline(headline: str) -> str:
    lowered = headline.strip().lower()
    stripped = _NON_ALNUM.sub(" ", lowered)
    return _WHITESPACE.sub(" ", stripped).strip()


def dedup_hash(headline: str, published_at: datetime) -> str:
    key = f"{normalize_headline(headline)}|{published_at.date().isoformat()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
