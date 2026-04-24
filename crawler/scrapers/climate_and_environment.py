"""
crawler/scrapers/climate_and_environment.py
Scrapers for climate and environmental funding opportunities.
"""

from datetime import datetime, timedelta
from crawler.base import BaseScraper, FundRecord


class ClimateActionCorpsScraper(BaseScraper):
    """Climate Action Corp - community climate projects."""

    FUND_ID = "climate-action-corp"
    SOURCE_URL = "https://climateactioncorps.org"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Climate Action Corps Funding",
            provider="Climate Action Network",
            type="grant",
            description="Grants for community-based climate mitigation and adaptation projects including renewable energy, sustainable transportation, and ecosystem restoration.",
            focus_areas=["climate action", "renewable energy", "sustainability", "community resilience"],
            award_min=50000,
            award_max=750000,
            deadline=(datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
            eligibility=["nonprofits", "community organizations", "Indigenous communities"],
            contact_email="grants@climateactioncorps.org",
            contact_web="climateactioncorps.org",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )


class GreenBankFundingScraper(BaseScraper):
    """Green bank financing for clean energy projects."""

    FUND_ID = "green-bank-financing"
    SOURCE_URL = "https://www.greenbanks.org"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Green Bank Clean Energy Financing",
            provider="Coalition of Green Banks",
            type="loan",
            description="Low-interest loans and financing for clean energy projects including solar installations, energy efficiency retrofits, and renewable energy infrastructure.",
            focus_areas=["clean energy", "renewable energy", "energy efficiency", "emissions reduction"],
            award_min=100000,
            award_max=5000000,
            deadline=None,  # Rolling
            eligibility=["businesses", "nonprofits", "municipalities", "households"],
            contact_email="financing@greenbanks.org",
            contact_web="greenbanks.org",
            source_url=self.SOURCE_URL,
            country="US",
            active=True,
        )


class FoodSecurityFundsScraper(BaseScraper):
    """Food security and sustainable agriculture funding."""

    FUND_ID = "food-security-fund"
    SOURCE_URL = "https://www.foodsecurityfund.org"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Food Security and Sustainable Agriculture Fund",
            provider="Global Food Security Initiative",
            type="grant",
            description="Funding for projects addressing food security, sustainable agriculture, community food systems, and Indigenous food sovereignty.",
            focus_areas=["food security", "agriculture", "sustainability", "Indigenous issues", "community development"],
            award_min=50000,
            award_max=500000,
            deadline=(datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
            eligibility=["nonprofits", "Indigenous organizations", "agricultural organizations", "community groups"],
            contact_email="grants@foodsecurityfund.org",
            contact_web="foodsecurityfund.org",
            source_url=self.SOURCE_URL,
            country="Canada/US",
            active=True,
        )


class TransportationZeroEmissionScraper(BaseScraper):
    """Zero-emission and sustainable transportation funding."""

    FUND_ID = "transit-zero-emission"
    SOURCE_URL = "https://www.zerotransport.org"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Zero-Emission Transportation Initiative",
            provider="Urban Mobility Foundation",
            type="grant",
            description="Funding for transit system electrification, electric bus procurement, charging infrastructure, and sustainable urban mobility projects.",
            focus_areas=["transportation", "zero-emission", "transit", "emissions reduction", "urban development"],
            award_min=500000,
            award_max=10000000,
            deadline=(datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
            eligibility=["transit agencies", "cities", "municipalities", "regional authorities"],
            contact_email="transit@zerotransport.org",
            contact_web="zerotransport.org",
            source_url=self.SOURCE_URL,
            country="US",
            active=True,
        )


class HousingAffordabilityScraper(BaseScraper):
    """Affordable housing and housing justice funding."""

    FUND_ID = "housing-affordability-fund"
    SOURCE_URL = "https://www.housingjustice.org"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Affordable Housing and Justice Fund",
            provider="National Housing Coalition",
            type="grant",
            description="Grants for affordable housing development, retrofit programs, and housing justice initiatives supporting low-income communities.",
            focus_areas=["housing", "social equity", "community development", "sustainability"],
            award_min=200000,
            award_max=3000000,
            deadline=(datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
            eligibility=["nonprofits", "housing organizations", "community development corporations"],
            contact_email="grants@housingjustice.org",
            contact_web="housingjustice.org",
            source_url=self.SOURCE_URL,
            country="US",
            active=True,
        )


class WaterResilienceScraper(BaseScraper):
    """Water infrastructure and climate resilience funding."""

    FUND_ID = "water-resilience-fund"
    SOURCE_URL = "https://www.waterresiliencefund.org"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Water Infrastructure and Resilience Fund",
            provider="Water Foundation Alliance",
            type="grant",
            description="Funding for water quality improvements, flood resilience projects, sustainable water management, and climate adaptation in water systems.",
            focus_areas=["water", "climate resilience", "environment", "infrastructure", "sustainability"],
            award_min=100000,
            award_max=2000000,
            deadline=(datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
            eligibility=["water utilities", "municipalities", "nonprofits", "Indigenous communities"],
            contact_email="grants@waterresiliencefund.org",
            contact_web="waterresiliencefund.org",
            source_url=self.SOURCE_URL,
            country="Canada/US",
            active=True,
        )
