"""
Companies House API client for downloading financial documents
"""

import asyncio
import structlog
from typing import List, Optional, Dict, Any
import aiohttp
from datetime import datetime
import os

from app.models.club import ClubFinancialData
from app.services.azure_search.blob_manager import BlobStorageManager

logger = structlog.get_logger()


class CompaniesHouseClient:
    """Client for interacting with Companies House API"""
    
    def __init__(self):
        self.base_url = os.getenv('COMPANIES_HOUSE_BASE_URL', 'https://api.company-information.service.gov.uk')
        self.api_key = os.getenv('COMPANIES_HOUSE_API_KEY')
        self.blob_manager = BlobStorageManager()
        
        # Rate limiting: 600 requests per 5 minutes = 1 request every 0.5 seconds
        self.rate_limit_delay = 0.5
        
    async def _make_request(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict[Any, Any]]:
        """Make authenticated request to Companies House API with rate limiting"""
        
        # Basic auth with API key as username, empty password
        auth = aiohttp.BasicAuth(self.api_key, '')
        
        try:
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            async with session.get(url, auth=auth, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    logger.warning("Resource not found", url=url)
                    return None
                elif response.status == 429:
                    logger.warning("Rate limit exceeded, waiting longer")
                    await asyncio.sleep(2)
                    return await self._make_request(session, url)
                else:
                    logger.error("API request failed", 
                               status=response.status, 
                               url=url)
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("Request timeout", url=url)
            return None
        except Exception as e:
            logger.error("Request failed", url=url, error=str(e))
            return None
    
    async def get_company_filing_history(self, company_number: str) -> Optional[List[Dict[Any, Any]]]:
        """Get filing history for a company"""
        
        company_number = company_number.zfill(8)
        url = f"{self.base_url}/company/{company_number}/filing-history"
        
        params = {
            'category': 'accounts',
            'items_per_page': 10
        }
        
        url_with_params = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        
        async with aiohttp.ClientSession() as session:
            data = await self._make_request(session, url_with_params)
            
            if data and 'items' in data:
                # Filter for actual account filings
                account_filings = []
                for filing in data['items']:
                    description = filing.get('description', '').lower()
                    
                    if any(keyword in description for keyword in [
                        'accounts-with-accounts-type',
                        'accounts-amended-with',
                        'annual accounts',
                        'full accounts',
                        'abbreviated accounts'
                    ]):
                        account_filings.append(filing)
                
                logger.info("Retrieved filing history", 
                          company_number=company_number,
                          total_filings=len(data['items']),
                          account_filings=len(account_filings))
                
                return account_filings
            
            return []
    
    async def get_company_profile(self, company_number: str) -> Optional[Dict[Any, Any]]:
        """Get company profile for fallback made_up_date"""
        
        company_number = company_number.zfill(8)
        url = f"{self.base_url}/company/{company_number}"
        
        async with aiohttp.ClientSession() as session:
            data = await self._make_request(session, url)
            
            if data:
                logger.info("Retrieved company profile", company_number=company_number)
            
            return data
    
    async def download_filing_document(self, company_number: str, filing_id: str) -> Optional[bytes]:
        """Download PDF document for a specific filing"""
        
        company_number = company_number.zfill(8)
        url = f"{self.base_url}/company/{company_number}/filing-history/{filing_id}/document"
        
        auth = aiohttp.BasicAuth(self.api_key, '')
        
        try:
            await asyncio.sleep(self.rate_limit_delay)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth, timeout=60) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        logger.info("Downloaded filing document",
                                  company_number=company_number,
                                  filing_id=filing_id,
                                  size_kb=len(content) // 1024)
                        
                        return content
                    else:
                        logger.error("Failed to download document",
                                   company_number=company_number,
                                   filing_id=filing_id,
                                   status=response.status)
                        return None
                        
        except Exception as e:
            logger.error("Document download failed",
                        company_number=company_number,
                        filing_id=filing_id,
                        error=str(e))
            return None
        
    async def download_document_from_url(self, document_url: str) -> Optional[bytes]:
        """Download PDF document from document metadata URL"""
        
        auth = aiohttp.BasicAuth(self.api_key, '')
        
        try:
            await asyncio.sleep(self.rate_limit_delay)
            
            async with aiohttp.ClientSession() as session:
                # Step 1: Get document metadata (JSON)
                async with session.get(document_url, auth=auth, headers={'Accept': 'application/json'}) as response:
                    if response.status == 200:
                        metadata = await response.json()
                        
                        # Step 2: Extract actual PDF download URL
                        pdf_url = metadata.get('links', {}).get('document')
                        if not pdf_url:
                            logger.error("No document link found in metadata")
                            return None
                        
                        # Ensure the URL has /content suffix for PDF
                        if not pdf_url.endswith('/content'):
                            pdf_url += '/content'
                        
                        logger.info("Found PDF download URL", pdf_url=pdf_url)
                        
                        # Step 3: Download the actual PDF
                        await asyncio.sleep(self.rate_limit_delay)  # Rate limit second request
                        
                        async with session.get(pdf_url, auth=auth, headers={'Accept': 'application/pdf'}) as pdf_response:
                            if pdf_response.status == 200:
                                content = await pdf_response.read()
                                
                                # Validate PDF content
                                if content and len(content) > 1024 and content.startswith(b'%PDF'):
                                    logger.info("Downloaded valid PDF document",
                                            pdf_url=pdf_url,
                                            size_kb=len(content) // 1024)
                                    return content
                                else:
                                    logger.error("Invalid PDF content received",
                                            size=len(content) if content else 0,
                                            header=content[:10] if content else None)
                                    return None
                            else:
                                logger.error("Failed to download PDF",
                                        pdf_url=pdf_url,
                                        status=pdf_response.status)
                                return None
                    else:
                        logger.error("Failed to get document metadata",
                                document_url=document_url,
                                status=response.status)
                        return None
                        
        except Exception as e:
            logger.error("Document download failed",
                        document_url=document_url,
                        error=str(e))
            return None