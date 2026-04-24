"""
crawler/base.py
Abstract base class for all fund scrapers.
Each funder gets its own subclass in crawler/scrapers/.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FundRecord:
    """
    Canonical data model for a fund.
    Must match the structure in data/funds.json.
    """
    id:             str
    name:           str
    provider:       str
    type:           str                    # "grant" | "loan" | "rebate"
    description:    str
    focus_areas:    list[str]
    award_min:      Optional[int]
    award_max:      Optional[int]
    deadline:       Optional[str]          # ISO 8601: "2026-05-01" or None for rolling
    eligibility:    list[str]
    contact_email:  str
    contact_web:    str
    source_url:     str
    country:        str = "Canada"         # "Canada", "US", or "Canada/US"
    active:         bool = True
    last_verified:  str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class BaseScraper(ABC):
    """
    All scrapers must implement scrape() and return a FundRecord.
    The run() method handles HTTP, error catching, and change detection.
    """

    # Override in subclass
    FUND_ID:    str = ""
    SOURCE_URL: str = ""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = self._make_session()

    def _make_session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; FundMatchBot/1.0; "
                "+https://github.com/your-org/fundmatch)"
            )
        })
        return session

    def fetch(self, url: str) -> str:
        """GET a URL and return the response text."""
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    @abstractmethod
    def scrape(self) -> FundRecord:
        """
        Fetch and parse the funder page.
        Return a populated FundRecord.
        Raise an exception if the fund can't be parsed or is no longer active.
        """
        ...

    def run(self) -> tuple[FundRecord | None, str]:
        """
        Execute the scraper with error handling.

        Returns:
            (record, status) where status is one of:
            "updated" | "unchanged" | "inactive" | "error"
        """
        try:
            record = self.scrape()
            return record, "updated"
        except FundInactiveError:
            logger.warning(f"[{self.FUND_ID}] Fund appears inactive or closed.")
            return None, "inactive"
        except Exception as e:
            logger.error(f"[{self.FUND_ID}] Scrape failed: {e}")
            return None, "error"


class FundInactiveError(Exception):
    """Raise this in scrape() when a fund page indicates it is closed."""
    pass


# ---------------------------------------------------------------------------
# Fund database helpers used by run_crawl.py
# ---------------------------------------------------------------------------

FUNDS_PATH = Path("data/funds.json")


def load_db() -> dict[str, dict]:
    """Load funds.json as a dict keyed by fund id."""
    if not FUNDS_PATH.exists():
        return {}
    with open(FUNDS_PATH) as f:
        funds = json.load(f)
    return {fund["id"]: fund for fund in funds}


def save_db(db: dict[str, dict]) -> None:
    """Write the fund dict back to funds.json as a sorted list."""
    funds = sorted(db.values(), key=lambda f: f["id"])
    with open(FUNDS_PATH, "w") as f:
        json.dump(funds, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(funds)} funds to {FUNDS_PATH}")


def apply_update(db: dict[str, dict], record: FundRecord) -> str:
    """
    Merge a scraped record into the fund database.

    Returns:
        "new" if the fund wasn't in the db before,
        "changed" if any tracked fields changed,
        "unchanged" if nothing changed.
    """
    TRACKED_FIELDS = {"deadline", "description", "award_min", "award_max", "active"}
    new_data = record.to_dict()

    if record.id not in db:
        db[record.id] = new_data
        return "new"

    existing = db[record.id]
    changed = any(
        existing.get(k) != new_data.get(k)
        for k in TRACKED_FIELDS
    )

    # Always update last_verified
    existing.update(new_data)

    return "changed" if changed else "unchanged"
