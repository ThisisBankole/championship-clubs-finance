"""
API endpoints - all in one file for simplicity
"""

import structlog
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from app.models.club import ClubFinancialData
from app.services.companies_house.processor import NationalLeagueProcessor
from app.services.search_service import FinancialSearchService
from app.api.endpoints import skillset_endpoints
from app.api.endpoints import financial_extraction
from app.api.endpoints import search_management


logger = structlog.get_logger()

api_router = APIRouter()

api_router.include_router(
    skillset_endpoints.router,
    prefix="/skillsets", 
    tags=["azure-ai-search-skills"]
)


api_router.include_router(
    financial_extraction.router,
    prefix="/financial-extraction",
    tags=["financial-extraction"]
)

api_router.include_router(
    search_management.router,
    prefix="/search-management",
    tags=["search-management"]
)


@api_router.post("/processing/download-all-documents", response_model=List[ClubFinancialData])
async def download_all_documents():
    """
    Download and process financial documents for all 24 National League clubs
    
    This endpoint will:
    1. Get latest filing information from Companies House for all 24 clubs
    2. Download PDF documents 
    3. Upload PDFs to Azure Blob Storage
    4. Trigger Azure AI Search processing automatically
    
    Returns summary of processing results for each club.
    """
    
    logger.info("Starting document processing for all National League clubs")
    
    try:
        processor = NationalLeagueProcessor()
        results = await processor.process_all_clubs(max_concurrent=3)
        
        # Create summary statistics
        successful = len([r for r in results if r.status == "success"])
        failed = len([r for r in results if r.status != "success"])
        
        logger.info("Document processing completed",
                   total_clubs=len(results),
                   successful=successful,
                   failed=failed)
        
        return results
        
    except Exception as e:
        logger.error("Document processing failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )


@api_router.post("/processing/download-single-club/{club_name}", response_model=ClubFinancialData)
async def download_single_club(club_name: str):
    """
    Download and process financial documents for a specific club
    
    Args:
        club_name: Name of the club (e.g., "Aldershot Town", "Forest Green Rovers")
    
    Returns club processing result.
    """
    
    logger.info("Starting document processing for single club", club_name=club_name)
    
    try:
        processor = NationalLeagueProcessor()
        result = await processor.process_club_by_name(club_name)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Club '{club_name}' not found in National League database"
            )
        
        logger.info("Single club processing completed",
                   club_name=club_name,
                   status=result.status)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Single club processing failed", 
                    club_name=club_name, 
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed for {club_name}: {str(e)}"
        )


@api_router.get("/processing/clubs", response_model=List[dict])
async def list_clubs():
    """
    Get list of all 24 National League clubs available for processing
    
    Returns basic information about each club including company numbers.
    """
    
    processor = NationalLeagueProcessor()
    
    return [
        {
            "club_name": club["club_name"],
            "company_number": club["company_number"],
            "legal_name": club["legal_name"]
        }
        for club in processor.CLUBS_DATA
    ]


@api_router.get("/processing/processing-status")
async def get_processing_status():
    """
    Get current processing status and system health
    
    Returns information about Azure connections and API availability.
    """
    
    # Basic health check information
    return {
        "service": "National League Document Processor",
        "status": "ready",
        "total_clubs": 24,
        "supported_operations": [
            "download-all-documents",
            "download-single-club", 
            "list-clubs"
        ],
        "rate_limits": {
            "companies_house": "600 requests per 5 minutes",
            "concurrent_processing": "3 clubs at once"
        }
    }
    
@api_router.get("/clubs")
async def get_all_clubs():
    """Get all clubs with structured club information"""
    search_service = FinancialSearchService()
    results = await search_service.search_with_club_info()
    
    return {
        "total": len(results),
        "clubs": results
    }

@api_router.get("/clubs/{club_name}")
async def get_club_by_name(club_name: str):
    """Get specific club data by name"""
    search_service = FinancialSearchService()
    
    # Search using the clean club_name field
    query = f'club_name:"{club_name}"'
    results = await search_service.search_with_club_info(query)
    
    if not results:
        # Fallback: partial match
        query = f'club_name:*{club_name}*'
        results = await search_service.search_with_club_info(query)
    
    return {
        "club_name": club_name,
        "found": len(results),
        "documents": results
    }

@api_router.get("/clubs/company/{company_number}")
async def get_club_by_company_number(company_number: str):
    """Get club by company registration number"""
    search_service = FinancialSearchService()
    
    query = f'company_number:"{company_number}"'
    results = await search_service.search_with_club_info(query)
    
    return {
        "company_number": company_number,
        "found": len(results),
        "documents": results
    }