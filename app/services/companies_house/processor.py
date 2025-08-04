"""
National League processor with all 24 clubs hardcoded
"""

import asyncio
import structlog
from typing import List, Dict, Optional
from datetime import datetime

from app.services.companies_house.client import CompaniesHouseClient
from app.models.club import ClubFinancialData

logger = structlog.get_logger()


class NationalLeagueProcessor:
    """Processes all 24 National League clubs"""
    
    CLUBS_DATA = [
    {"club_name": "Birmingham City", "company_number": "00027318", "legal_name": "BIRMINGHAM CITY FOOTBALL CLUB LIMITED"},
    {"club_name": "Blackburn Rovers", "company_number": "00053482", "legal_name": "THE BLACKBURN ROVERS FOOTBALL AND ATHLETIC LIMITED"},
    {"club_name": "Bristol City", "company_number": "03230871", "legal_name": "BRISTOL CITY FOOTBALL CLUB LIMITED"},
    {"club_name": "Charlton Athletic", "company_number": "01788466", "legal_name": "CHARLTON ATHLETIC FOOTBALL COMPANY LIMITED"},
    {"club_name": "Coventry City", "company_number": "07612487", "legal_name": "COVENTRY CITY FOOTBALL CLUB LIMITED"},
    {"club_name": "Derby County", "company_number": "00049139", "legal_name": "THE DERBY COUNTY FOOTBALL CLUB LIMITED"},
    {"club_name": "Hull City", "company_number": "04032392", "legal_name": "HULL CITY TIGERS LIMITED"},
    {"club_name": "Ipswich Town", "company_number": "00315421", "legal_name": "IPSWICH TOWN FOOTBALL CLUB COMPANY LIMITED"},
    {"club_name": "Leicester City", "company_number": "04593477", "legal_name": "LEICESTER CITY FOOTBALL CLUB LIMITED"},
    {"club_name": "Middlesbrough", "company_number": "01947851", "legal_name": "MIDDLESBROUGH FOOTBALL & ATHLETIC COMPANY (1986) LIMITED"},
    {"club_name": "Millwall", "company_number": "02355508", "legal_name": "MILLWALL HOLDINGS PLC"},
    {"club_name": "Norwich City", "company_number": "00154044", "legal_name": "NORWICH CITY FOOTBALL CLUB PLC"},
    {"club_name": "Oxford United", "company_number": "00470509", "legal_name": "OXFORD UNITED FOOTBALL CLUB LIMITED"},
    {"club_name": "Portsmouth", "company_number": "07940335", "legal_name": "PORTSMOUTH COMMUNITY FOOTBALL CLUB LIMITED"},
    {"club_name": "Preston North End", "company_number": "00039494", "legal_name": "PRESTON NORTH END FOOTBALL CLUB,LIMITED(THE)"},
    {"club_name": "Queens Park Rangers", "company_number": "00060094", "legal_name": "QUEENS PARK RANGERS FOOTBALL & ATHLETIC CLUB,LIMITED,(THE)"},
    {"club_name": "Sheffield United", "company_number": "00061564", "legal_name": "THE SHEFFIELD UNITED FOOTBALL CLUB LIMITED"},
    {"club_name": "Sheffield Wednesday", "company_number": "02509978", "legal_name": "SHEFFIELD WEDNESDAY FOOTBALL CLUB LIMITED"},
    {"club_name": "Southampton", "company_number": "00053301", "legal_name": "SOUTHAMPTON FOOTBALL CLUB LIMITED"},
    {"club_name": "Stoke City", "company_number": "00099885", "legal_name": "STOKE CITY FOOTBALL CLUB LIMITED"},
    {"club_name": "Swansea City", "company_number": "04056708", "legal_name": "SWANSEA CITY FOOTBALL CLUB LIMITED"},
    {"club_name": "Watford", "company_number": "00104194", "legal_name": "WATFORD ASSOCIATION FOOTBALL CLUB LIMITED(THE)"},
    {"club_name": "West Bromwich Albion", "company_number": "03295063", "legal_name": "WEST BROMWICH ALBION FOOTBALL CLUB LIMITED"},
    {"club_name": "Wrexham", "company_number": "07698872", "legal_name": "Wrexham AFC Limited"}
]
    
    def __init__(self):
        self.client = CompaniesHouseClient()
        
    @staticmethod
    def create_safe_club_name(club_name: str) -> str:
        """Create URL-safe company name for blob paths"""
        
        # Convert to lowercase
        name = club_name.lower()
        
        # Remove common suffixes
        name = name.replace(' football club', '')
        name = name.replace(' fc', '')
        name = name.replace(' united', '-united')
        name = name.replace(' town', '-town')
        name = name.replace(' city', '-city')
        
        # Replace spaces and special characters
        name = name.replace(' ', '-')
        name = name.replace('&', 'and')
        name = name.replace("'", '')
        
        # Remove multiple dashes and clean up
        import re
        name = re.sub(r'-+', '-', name)
        name = name.strip('-')
        
        return name
    
    async def process_single_club(self, club_data: Dict[str, str]) -> ClubFinancialData:
        """Process a single club's filings"""
        
        club_name = club_data['club_name']
        company_number = club_data['company_number']
        
        logger.info("Processing club", club_name=club_name, company_number=company_number)
        
        try:
            # Get filing history
            filings = await self.client.get_company_filing_history(company_number)
            
            if not filings:
                logger.warning("No filings found", club_name=club_name)
                return ClubFinancialData(
                    club_name=club_name,
                    company_number=company_number,
                    legal_name=club_data['legal_name'],
                    status="no_filings",
                    error_message="No account filings found"
                )
            
            # Get the latest filing
            latest_filing = filings[0]
            
            # Extract made_up_date with fallback
            made_up_date = latest_filing.get('made_up_date')
            
            if not made_up_date:
                # Fallback: get from company profile
                profile = await self.client.get_company_profile(company_number)
                if profile and 'accounts' in profile:
                    accounts = profile['accounts']
                    if 'last_accounts' in accounts:
                        made_up_date = accounts['last_accounts'].get('made_up_to')
            
            # Download and upload PDF
            pdf_uploaded = False
         
            
            # Extract filing ID from links
            if 'links' in latest_filing and 'document_metadata' in latest_filing['links']:
                document_url = latest_filing['links']['document_metadata']
                
                # Download PDF
                pdf_content = await self.client.download_document_from_url(document_url)
                
                if pdf_content:
                    # Upload to blob storage
                    safe_company_name = self.create_safe_club_name(club_name)
                    blob_path = f"{company_number.zfill(8)}-{safe_company_name}/{made_up_date or 'unknown'}/accounts.pdf"
                    pdf_uploaded = await self.client.blob_manager.upload_pdf(blob_path, pdf_content)
            
            # Create result
            result = ClubFinancialData(
                club_name=club_name,
                company_number=company_number,
                legal_name=club_data['legal_name'],
                filing_date=latest_filing.get('date'),
                accounts_year_end=made_up_date,
                filing_year=made_up_date[:4] if made_up_date else None,
                description=latest_filing.get('description'),
                pdf_uploaded=pdf_uploaded,
                status="success" if pdf_uploaded else "pdf_upload_failed"
            )
            
            logger.info("Completed club processing",
                       club_name=club_name,
                       pdf_uploaded=pdf_uploaded,
                       accounts_year_end=made_up_date)
            
            return result
            
        except Exception as e:
            logger.error("Error processing club", club_name=club_name, error=str(e))
            return ClubFinancialData(
                club_name=club_name,
                company_number=company_number,
                legal_name=club_data['legal_name'],
                status="error",
                error_message=str(e)
            )
    
    async def process_all_clubs(self, max_concurrent: int = 3) -> List[ClubFinancialData]:
        """Process all 24 National League clubs with concurrency control"""
        
        logger.info("Starting processing of all National League clubs",
                   total_clubs=len(self.CLUBS_DATA),
                   max_concurrent=max_concurrent)
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(club_data):
            async with semaphore:
                return await self.process_single_club(club_data)
        
        # Process all clubs concurrently
        start_time = datetime.now()
        
        tasks = [process_with_semaphore(club) for club in self.CLUBS_DATA]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Club processing failed",
                           club_name=self.CLUBS_DATA[i]['club_name'],
                           error=str(result))
                
                processed_results.append(ClubFinancialData(
                    club_name=self.CLUBS_DATA[i]['club_name'],
                    company_number=self.CLUBS_DATA[i]['company_number'],
                    legal_name=self.CLUBS_DATA[i]['legal_name'],
                    status="error",
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        # Log summary
        successful = len([r for r in processed_results if r.status == "success"])
        failed = len([r for r in processed_results if r.status != "success"])
        
        logger.info("Completed processing all clubs",
                   total_clubs=len(self.CLUBS_DATA),
                   successful=successful,
                   failed=failed,
                   duration_seconds=duration)
        
        return processed_results
    
    async def process_club_by_name(self, club_name: str) -> Optional[ClubFinancialData]:
        """Process a single club by name"""
        
        club_data = next((club for club in self.CLUBS_DATA if club['club_name'] == club_name), None)
        
        if not club_data:
            logger.error("Club not found", club_name=club_name)
            return None
        
        return await self.process_single_club(club_data)