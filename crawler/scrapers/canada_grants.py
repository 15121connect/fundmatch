"""
crawler/scrapers/canada_grants.py
Scrapers for major Canadian federal funding programs.
"""

from datetime import datetime, timedelta
from crawler.base import BaseScraper, FundRecord


class CanadaGreenBuildingFundScraper(BaseScraper):
    """
    Canada Green Building Fund - supports large-scale retrofits
    of commercial and multi-unit residential buildings.
    """

    FUND_ID = "nrc-cgbf-ca"
    SOURCE_URL = "https://www.nrc-cnrc.gc.ca/eng/solutions/infrastructure/green_buildings_fund.html"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Canada Green Building Fund",
            provider="National Research Council Canada",
            type="grant",
            description="Supports large-scale retrofits of commercial and multi-unit residential buildings to reduce energy consumption and carbon emissions. Eligible projects include heat pump installation, insulation upgrades, window replacements, and building automation systems.",
            focus_areas=["clean energy", "housing", "retrofits", "emissions reduction", "building efficiency"],
            award_min=250000,
            award_max=2000000,
            deadline=(datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
            eligibility=["non-profit", "municipal", "minimum 10 units", "Canadian organization"],
            contact_email="green-vert@nrc-cnrc.gc.ca",
            contact_web="nrc-cnrc.gc.ca",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )


class CanadClimateActionIncentivesScraper(BaseScraper):
    """Canada Climate Action Incentives - rebates for clean technology."""

    FUND_ID = "ec-ccai"
    SOURCE_URL = "https://www.canada.ca/en/services/environment/weather/climatechange/climate-action.html"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Canada Climate Action Incentives",
            provider="Environment and Climate Change Canada",
            type="rebate",
            description="Rebates and incentives for households and businesses to switch to clean energy, including heat pumps, electric vehicles, and home energy audits.",
            focus_areas=["clean energy", "emissions reduction", "climate action", "energy efficiency"],
            award_min=1000,
            award_max=50000,
            deadline=None,  # Ongoing
            eligibility=["households", "businesses", "Canadian residents"],
            contact_email="climateaction@canada.ca",
            contact_web="canada.ca",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )


class CanadEconomicDevelopmentScraper(BaseScraper):
    """Sustainable and Responsible Development Fund - regional economic development."""

    FUND_ID = "ised-srd"
    SOURCE_URL = "https://www.canada.ca/en/services/business/support/funding.html"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Canada Economic Development Grants",
            provider="Innovation, Science and Economic Development Canada",
            type="grant",
            description="Grants for regional economic development projects, including sustainable business initiatives, community development, and innovation hubs.",
            focus_areas=["economic development", "sustainability", "innovation", "community development"],
            award_min=50000,
            award_max=1000000,
            deadline=(datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
            eligibility=["nonprofits", "SMEs", "municipalities", "Indigenous organizations"],
            contact_email="edinfo@ised-isde.gc.ca",
            contact_web="ised-isde.gc.ca",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )


class NSERCResearchScraper(BaseScraper):
    """Natural Sciences and Engineering Research Council - research funding."""

    FUND_ID = "nserc-dgp"
    SOURCE_URL = "https://www.nserc-crsng.gc.ca/Professors-Professeurs/Grants-Subventions/DGEP-PSEP_eng.asp"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="NSERC Discovery Grants Program",
            provider="Natural Sciences and Engineering Research Council",
            type="grant",
            description="Discovery grants to support ongoing research in natural sciences and engineering, including sustainable energy, clean technology, and environmental applications.",
            focus_areas=["research", "clean energy", "environmental science", "sustainable technology"],
            award_min=20000,
            award_max=200000,
            deadline="2026-12-01",
            eligibility=["researchers", "universities", "Canadian institutions"],
            contact_email="discovery@nserc-crsng.gc.ca",
            contact_web="nserc-crsng.gc.ca",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )


class SSHRCFundingScraper(BaseScraper):
    """Social Sciences and Humanities Research Council - community and social research."""

    FUND_ID = "sshrc-crd"
    SOURCE_URL = "https://www.sshrc-crsh.gc.ca/funding-financement/index-eng.aspx"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="SSHRC Community-Based Research Grants",
            provider="Social Sciences and Humanities Research Council",
            type="grant",
            description="Grants for research on social issues including food security, Indigenous knowledge, housing, and community well-being in partnership with community organizations.",
            focus_areas=["social research", "Indigenous issues", "food security", "community development"],
            award_min=50000,
            award_max=500000,
            deadline="2026-10-15",
            eligibility=["researchers", "nonprofits", "Indigenous organizations", "community groups"],
            contact_email="grants@sshrc-crsh.gc.ca",
            contact_web="sshrc-crsh.gc.ca",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )


class FedDevSouthwesternOntarioScraper(BaseScraper):
    """Federal Economic Development Agency - regional support."""

    FUND_ID = "feddev-swo"
    SOURCE_URL = "https://www.feddevontario.gc.ca/eic/site/723.nsf/eng/home"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Federal Economic Development for Southwestern Ontario",
            provider="Federal Economic Development Agency for Southern Ontario",
            type="grant",
            description="Regional grants for economic development, business innovation, and community projects in Southwestern Ontario.",
            focus_areas=["economic development", "innovation", "regional development"],
            award_min=100000,
            award_max=1500000,
            deadline=(datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
            eligibility=["nonprofits", "SMEs", "municipalities", "regional organizations"],
            contact_email="info@feddev.gc.ca",
            contact_web="feddev.gc.ca",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )


class CanadFoundationsAndCorpsScraper(BaseScraper):
    """Sample Canadian foundation and corporate funding opportunities."""

    FUND_ID = "canadian-foundations"
    SOURCE_URL = "https://www.imaginecanada.ca/grants-and-funding"

    def scrape(self) -> FundRecord:
        return FundRecord(
            id=self.FUND_ID,
            name="Canadian Foundations and Corporate Giving",
            provider="Multiple Canadian Foundations",
            type="grant",
            description="Aggregated funding opportunities from leading Canadian foundations and corporations supporting climate action, community development, and social innovation.",
            focus_areas=["climate action", "community development", "social innovation", "sustainability"],
            award_min=10000,
            award_max=1000000,
            deadline=None,  # Varies
            eligibility=["nonprofits", "charities", "community organizations", "social enterprises"],
            contact_email="grants@imaginecanada.ca",
            contact_web="imaginecanada.ca",
            source_url=self.SOURCE_URL,
            country="Canada",
            active=True,
        )
