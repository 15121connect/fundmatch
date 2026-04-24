"""
crawler/run_crawl.py
Entry point for the scheduled crawl job.
Run manually:    python -m crawler.run_crawl
Run via GitHub Actions: see .github/workflows/crawl.yml

Discovers all scrapers in crawler/scrapers/, runs them, merges
results into data/funds.json, and prints a summary report.
"""

import importlib
import inspect
import logging
import sys
from pathlib import Path

from crawler.base import BaseScraper, load_db, save_db, apply_update

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def discover_scrapers() -> list[type[BaseScraper]]:
    """
    Auto-discover all BaseScraper subclasses in crawler/scrapers/.
    Add a new .py file there and it will be picked up automatically.
    """
    scrapers_dir = Path(__file__).parent / "scrapers"
    found = []

    for path in sorted(scrapers_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"crawler.scrapers.{path.stem}"
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logger.warning(f"Could not import {module_name}: {e}")
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseScraper)
                and obj is not BaseScraper
                and obj.FUND_ID  # skip abstract stubs
            ):
                found.append(obj)

    logger.info(f"Discovered {len(found)} scraper(s): {[s.FUND_ID for s in found]}")
    return found


def run_all(dry_run: bool = False) -> dict:
    """
    Run all scrapers and merge results into the fund database.

    Args:
        dry_run: If True, print changes without writing to disk.

    Returns:
        Summary dict with counts of new / changed / unchanged / inactive / error.
    """
    db = load_db()
    scraper_classes = discover_scrapers()

    summary = {
        "new":       [],
        "changed":   [],
        "unchanged": [],
        "inactive":  [],
        "error":     [],
    }

    for scraper_cls in scraper_classes:
        fund_id = scraper_cls.FUND_ID
        logger.info(f"Running scraper: {fund_id}")

        scraper = scraper_cls()
        record, run_status = scraper.run()

        if run_status == "error":
            summary["error"].append(fund_id)
            continue

        if run_status == "inactive":
            # Mark existing record inactive rather than deleting it
            if fund_id in db:
                db[fund_id]["active"] = False
                summary["inactive"].append(fund_id)
            continue

        # Merge into db
        change_status = apply_update(db, record)

        if change_status == "new":
            summary["new"].append(fund_id)
            logger.info(f"  → NEW fund added: {record.name}")
        elif change_status == "changed":
            summary["changed"].append(fund_id)
            logger.info(f"  → Updated: {record.name}")
        else:
            summary["unchanged"].append(fund_id)
            logger.info(f"  → No changes: {record.name}")

    if not dry_run:
        save_db(db)
    else:
        logger.info("[dry-run] Changes not written to disk.")

    _print_report(summary)
    return summary


def _print_report(summary: dict) -> None:
    total = sum(len(v) for v in summary.values())
    logger.info("=" * 50)
    logger.info(f"Crawl complete. {total} fund(s) processed.")
    logger.info(f"  New:       {len(summary['new'])}")
    logger.info(f"  Changed:   {len(summary['changed'])}")
    logger.info(f"  Unchanged: {len(summary['unchanged'])}")
    logger.info(f"  Inactive:  {len(summary['inactive'])}")
    logger.info(f"  Errors:    {len(summary['error'])}")
    if summary["error"]:
        logger.warning(f"  Failed:    {', '.join(summary['error'])}")
    logger.info("=" * 50)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_all(dry_run=dry_run)
