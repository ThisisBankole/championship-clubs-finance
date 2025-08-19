"""
API endpoints - all in one file for simplicity
"""
from app.services.cache.redis_cache import cache_service
import structlog
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from app.models.club import ClubFinancialData
from app.services.companies_house.processor import NationalLeagueProcessor
from app.services.search_service import FinancialSearchService
from app.api.endpoints import skillset_endpoints
from app.api.endpoints import financial_extraction
from app.api.endpoints import search_management
from app.api.endpoints import comprehensive_skillset
from app.api.endpoints import data_combiner
from app.api.endpoints import scheduler

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

api_router.include_router(
    comprehensive_skillset.router,
    prefix="/skillsets",
    tags=["comprehensive-skillset"]
)

api_router.include_router(
    data_combiner.router,
    prefix="/data-combiner",
    tags=["data-combiner"]
)

api_router.include_router(
    scheduler.router,
    prefix="/scheduler",
    tags=["scheduler"]
)


@api_router.post("/processing/download-all-documents", response_model=List[ClubFinancialData])
async def download_all_documents():
    """
    Download and process financial documents for all 24 National League clubs
    """
    
    logger.info("Starting document processing for all National League clubs")
    
    try:
        processor = NationalLeagueProcessor()
        results = await processor.process_all_clubs(max_concurrent=3)
        
        # Create summary statistics
        successful = len([r for r in results if r.status == "success"])
        failed = len([r for r in results if r.status != "success"])
        
        # Invalidate cache if any documents were processed successfully
        if successful > 0:
            cache_service.delete_pattern("clubs:*")
            cache_service.delete_pattern("clubs_search:*")
            logger.info("Invalidated clubs cache after document processing")
        
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
        
        # Invalidate cache if processing was successful
        if result.status == "success":
            cache_service.delete_pattern("clubs:*")
            cache_service.delete_pattern("clubs_search:*")
            logger.info("Invalidated clubs cache after single club processing", club_name=club_name)
        
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
    """Get all clubs with structured club information - CACHED"""
    
    # Check cache first
    cache_key = "clubs:all"
    cached_result = cache_service.get(cache_key)
    if cached_result:
        logger.info("Returning cached clubs data")
        return cached_result
    
    # Fetch from Azure Search
    search_service = FinancialSearchService()
    results = await search_service.search_with_club_info()
    
    response_data = {
        "total": len(results),
        "clubs": results,
        "cached_at": None  # Will be set when cached
    }
    
    # Cache for 30 minutes
    cache_service.set(cache_key, response_data, ttl=3600)
    logger.info("Cached clubs data", total_clubs=len(results))
    
    return response_data

@api_router.get("/clubs/{club_name}")
async def get_club_by_name(club_name: str):
    """Get specific club data by name - CACHED"""
    
    # Check cache first
    cache_key = f"clubs:by_name:{club_name.lower()}"
    cached_result = cache_service.get(cache_key)
    if cached_result:
        logger.info("Returning cached club data", club_name=club_name)
        return cached_result
    
    # Fetch from Azure Search
    search_service = FinancialSearchService()
    
    # Search using the clean club_name field
    query = f'club_name:"{club_name}"'
    results = await search_service.search_with_club_info(query)
    
    if not results:
        # Fallback: partial match
        query = f'club_name:*{club_name}*'
        results = await search_service.search_with_club_info(query)
    
    response_data = {
        "club_name": club_name,
        "found": len(results),
        "documents": results
    }
    
    # Cache individual club for 1 hour
    cache_service.set(cache_key, response_data, ttl=3600)
    logger.info("Cached individual club data", club_name=club_name)
    
    return response_data

@api_router.get("/clubs/company/{company_number}")
async def get_club_by_company_number(company_number: str):
    """Get club by company registration number - CACHED"""
    
    # Check cache first  
    cache_key = f"clubs:by_company:{company_number}"
    cached_result = cache_service.get(cache_key)
    if cached_result:
        logger.info("Returning cached club by company", company_number=company_number)
        return cached_result
    
    # Fetch from Azure Search
    search_service = FinancialSearchService()
    
    query = f'company_number:"{company_number}"'
    results = await search_service.search_with_club_info(query)
    
    response_data = {
        "company_number": company_number,
        "found": len(results),
        "documents": results
    }
    
    # Cache for 1 hour
    cache_service.set(cache_key, response_data, ttl=3600)
    logger.info("Cached club by company number", company_number=company_number)
    
    return response_data

@api_router.post("/cache/invalidate/clubs")
async def invalidate_clubs_cache():
    """Invalidate all clubs cache - call this when data is updated"""
    cache_service.delete_pattern("clubs:*")
    cache_service.delete_pattern("clubs_search:*")
    logger.info("Invalidated all clubs cache")
    return {"status": "success", "message": "Clubs cache invalidated"}

@api_router.get("/cache/status")
async def cache_status():
    """Get cache status"""
    return {
        "redis_connected": cache_service.redis_client is not None,
        "cache_active": True if cache_service.redis_client else False
    }