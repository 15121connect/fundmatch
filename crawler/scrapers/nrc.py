"""
crawler/scrapers/nrc.py
Scraper for the NRC Canada Green Building Fund.

Each scraper is a concrete example of the pattern — adapt the
CSS selectors and parsing logic for each funder's page structure.
"""

import re
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from crawler.base import BaseScraper, FundRecord, FundInactiveError


class NRCGreenBuildingScraper(BaseScraper):

    FUND_ID    = "nrc-cgbf"
    SOURCE_URL = "https://nrc.gc.ca/en/funding/green-building"

    # Keywords that suggest a fund page has closed
    CLOSED_SIGNALS = [
        "this program is closed",
        "applications are no longer",
        "intake has closed",
        "funding has been fully allocated",
    ]

    def scrape(self) -> FundRecord:
        html  = self.fetch(self.SOURCE_URL)
        soup  = BeautifulSoup(html, "html.parser")

        # Check for closure signals before parsing details
        page_text = soup.get_text(" ", strip=True).lower()
        if any(signal in page_text for signal in self.CLOSED_SIGNALS):
            raise FundInactiveError(f"{self.FUND_ID} page indicates fund is closed.")

        # ── Extract fields ──────────────────────────────────────────────────
        # These selectors are illustrative — update to match the live page DOM.

        name = self._extract_name(soup)
        description = self._extract_description(soup)
        deadline = self._extract_deadline(soup)
        award_min, award_max = self._extract_award_range(soup)

        return FundRecord(
            id            = self.FUND_ID,
            name          = name,
            provider      = "NRC Canada",
            type          = "grant",
            description   = description,
            focus_areas   = ["clean energy", "housing", "retrofits", "emissions reduction", "building efficiency"],
            award_min     = award_min,
            award_max     = award_max,
            deadline      = deadline,
            eligibility   = ["non-profit", "municipal", "minimum 10 units", "Canadian organization"],
            contact_email = "green-vert@nrc-cnrc.gc.ca",
            contact_web   = "nrc.gc.ca/green-building",
            source_url    = self.SOURCE_URL,
            country       = "Canada",
            active        = True,
        )

    def _extract_name(self, soup: BeautifulSoup) -> str:
        # Try h1, then fall back to title tag
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return soup.title.string.strip() if soup.title else "Canada Green Building Fund"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        # Look for a meta description or the first substantial paragraph
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        # Fallback: first paragraph with >100 chars
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 100:
                return text

        return ""

    def _extract_deadline(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Try to find a date near deadline-related keywords.
        Returns ISO date string or None for rolling.
        """
        text = soup.get_text(" ", strip=True)

        # Look for patterns like "Deadline: January 15, 2027" or "closes May 1, 2026"
        date_pattern = re.compile(
            r"(?:deadline|closes?|closing|due|submit by)[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
            re.IGNORECASE,
        )
        match = date_pattern.search(text)
        if match:
            return _parse_human_date(match.group(1))

        # ISO date near deadline keyword
        iso_pattern = re.compile(
            r"(?:deadline|closes?)[:\s]+(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE,
        )
        match = iso_pattern.search(text)
        if match:
            return match.group(1)

        return None  # rolling / no fixed deadline found

    def _extract_award_range(self, soup: BeautifulSoup) -> Tuple[Optional[int], Optional[int]]:
        """Extract min/max award amounts from the page."""
        text = soup.get_text(" ", strip=True)

        # Pattern: "$250,000 to $2,000,000" or "$250K to $2M"
        range_pattern = re.compile(
            r"\$(\d[\d,]*(?:\.\d+)?)\s*(?:to|-)\s*\$(\d[\d,]*(?:\.\d+)?)",
            re.IGNORECASE,
        )
        match = range_pattern.search(text)
        if match:
            lo = _parse_dollar(match.group(1))
            hi = _parse_dollar(match.group(2))
            return lo, hi

        # Single max: "up to $2,000,000"
        max_pattern = re.compile(
            r"up to \$(\d[\d,]*(?:\.\d+)?)",
            re.IGNORECASE,
        )
        match = max_pattern.search(text)
        if match:
            return None, _parse_dollar(match.group(1))

        return None, None


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _parse_human_date(text: str) -> Optional[str]:
    """Parse 'May 1, 2026' → '2026-05-01'."""
    from datetime import datetime
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parse_dollar(text: str) -> Optional[int]:
    """'2,000,000' or '2M' → 2000000."""
    text = text.replace(",", "").strip()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    suffix = text[-1].lower()
    if suffix in multipliers:
        try:
            return int(float(text[:-1]) * multipliers[suffix])
        except ValueError:
            return None
    try:
        return int(float(text))
    except ValueError:
        return None
