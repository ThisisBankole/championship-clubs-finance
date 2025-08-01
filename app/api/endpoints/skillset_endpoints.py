
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import structlog

from app.services.skillset.metadata_extractor import ClubMetadataExtractor

logger = structlog.get_logger()
router = APIRouter()

@router.post("/extract-club-metadata")
async def extract_club_metadata_skill(request_data: Dict[str, Any]):
    """
    Azure AI Search Custom Web API Skill
    Extracts club metadata from blob paths for search indexing
    """
    
    try:
        extractor = ClubMetadataExtractor()
        result = extractor.process_azure_search_request(request_data)
        
        logger.info("Processed club metadata extraction", 
                   records_processed=len(result.get('values', [])))
        
        return result
        
    except Exception as e:
        logger.error("Club metadata extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-metadata-extraction")
async def test_metadata_extraction(blob_paths: list[str]):
    """
    Test endpoint to verify metadata extraction logic
    """
    
    try:
        extractor = ClubMetadataExtractor()
        results = []
        
        for path in blob_paths:
            result = extractor.extract_from_blob_path(path)
            results.append({
                "blob_path": path,
                "extracted_data": result
            })
        
        return {
            "total_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error("Test metadata extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))