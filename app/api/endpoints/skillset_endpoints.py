
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import structlog

from app.services.skillset.metadata_extractor import ClubMetadataExtractor
from app.services.skillset.text_cleaner import TextCleaningService  # NEW IMPORT

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

# NEW ENDPOINT FOR TEXT CLEANING
@router.post("/clean-text-sections")
async def clean_text_sections_skill(request_data: Dict[str, Any]):
    """
    Azure AI Search Custom Web API Skill
    Cleans and extracts readable text from JSON-formatted OCR output
    
    This endpoint transforms your text_sections_content from JSON strings
    into clean text that can be processed by the financial extraction skill.
    """
    
    try:
        cleaner = TextCleaningService()
        result = cleaner.process_azure_search_request(request_data)
        
        logger.info("Processed text cleaning", 
                   records_processed=len(result.get('values', [])))
        
        return result
        
    except Exception as e:
        logger.error("Text section cleaning failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# UPDATED: Simple financial extraction for clean text input
@router.post("/extract-financials-simple")
async def extract_financials_simple_skill(request_data: Dict[str, Any]):
    """
    Azure AI Search Custom Web API Skill
    Extract financials from clean text (from Document Extraction skill)
    """
    try:
        from app.api.endpoints.financial_extraction import extract_financial_metrics_with_gpt4
        
        values = request_data.get('values', [])
        results = []
        
        for record in values:
            record_id = record.get('recordId', '')
            data = record.get('data', {})
            
            # Get clean text from Document Extraction skill
            text_content = data.get('text', '') or data.get('content', '') or data.get('extracted_content', '')
            
            logger.info("Processing financial extraction from clean text", 
                       record_id=record_id,
                       text_length=len(text_content))
            
            try:
                if text_content and len(text_content.strip()) > 50:
                    # Extract financials using your existing GPT-4 function
                    financial_data = await extract_financial_metrics_with_gpt4(text_content)
                    
                    # Convert Pydantic model to dict
                    financial_dict = financial_data.dict()
                    
                    # Remove None values to keep response clean
                    financial_dict = {k: v for k, v in financial_dict.items() if v is not None}
                    
                    results.append({
                        "recordId": record_id,
                        "data": financial_dict,
                        "errors": [],
                        "warnings": []
                    })
                    
                    logger.info("Successfully extracted financial data", 
                               record_id=record_id,
                               extracted_fields=len(financial_dict))
                else:
                    # No sufficient text content
                    results.append({
                        "recordId": record_id,
                        "data": {},  # Empty data, no errors
                        "errors": [],
                        "warnings": [{"message": f"Insufficient text content ({len(text_content)} chars)"}]
                    })
                    
            except Exception as e:
                logger.error("Financial extraction failed", record_id=record_id, error=str(e))
                
                # Return empty result on error (no data + errors rule)
                results.append({
                    "recordId": record_id,
                    "data": {},
                    "errors": [],
                    "warnings": [{"message": f"Extraction failed: {str(e)}"}]
                })
        
        logger.info("Completed financial extraction batch",
                   total_records=len(values),
                   successful_extractions=len([r for r in results if r.get('data')]))
        
        return {"values": results}
        
    except Exception as e:
        logger.error("Financial extraction skill failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        cleaner = TextCleaningService()
        
        # Extract text_sections from request
        text_sections = request.get('text_sections', [])
        
        if not text_sections:
            raise HTTPException(status_code=400, detail="text_sections field is required")
        
        # Extract text from JSON sections
        combined_text = cleaner.extract_text_from_json_sections(text_sections)
        
        # Clean the text
        cleaned_text = cleaner.clean_ocr_text(combined_text)
        
        # Analyze sections
        sections = cleaner._extract_sections(cleaned_text)
        
        return {
            "input_sections": len(text_sections),
            "original_length": len(combined_text),
            "cleaned_length": len(cleaned_text),
            "sections_found": sections,
            "preview": cleaned_text[:500],
            "full_cleaned_text": cleaned_text
        }
        
    except Exception as e:
        logger.error("Test text cleaning failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))