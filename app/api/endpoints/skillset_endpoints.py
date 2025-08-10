
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



@router.post("/extract-financials-simple")
async def extract_financials_simple_skill(request_data: Dict[str, Any]):
    """
    Azure AI Search Custom Web API Skill
    Extract financials from clean text (from Text Cleaning skill)
    """
    try:
        from app.api.endpoints.financial_extraction import extract_financial_metrics_with_gpt4
        
        values = request_data.get('values', [])
        results = []
        
        for record in values:
            record_id = record.get('recordId', '')
            data = record.get('data', {})
            
            # FIXED: Get clean text from Text Cleaning skill output
            # The text cleaning skill outputs 'cleaned_text', not 'text' or 'content'
            text_content = data.get('cleaned_text', '')
            
            logger.info("Processing financial extraction from cleaned text", 
                       record_id=record_id,
                       text_length=len(text_content),
                       available_fields=list(data.keys()))
            
            try:
                if text_content and len(text_content.strip()) > 50:
                    # Extract financials using your existing GPT-4 function
                    financial_data = await extract_financial_metrics_with_gpt4(text_content)
                    
                    # FIXED: Return data in the exact format your indexer expects
                    results.append({
                        "recordId": record_id,
                        "data": {
                            # Convert FinancialData object to dict for proper output mapping
                            "revenue": financial_data.revenue,
                            "turnover": financial_data.turnover,
                            "total_assets": financial_data.total_assets,
                            "total_liabilities": financial_data.total_liabilities,
                            "net_assets": financial_data.net_assets,
                            "cash_at_bank": financial_data.cash_at_bank,
                            "cash_and_cash_equivalents": financial_data.cash_and_cash_equivalents,
                            "creditors_due_within_one_year": financial_data.creditors_due_within_one_year,
                            "creditors_due_after_one_year": financial_data.creditors_due_after_one_year,
                            "operating_profit": financial_data.operating_profit,
                            "profit_loss_before_tax": financial_data.profit_loss_before_tax,
                            "broadcasting_revenue": financial_data.broadcasting_revenue,
                            "commercial_revenue": financial_data.commercial_revenue,
                            "matchday_revenue": financial_data.matchday_revenue,
                            "player_trading_income": financial_data.player_trading_income,
                            "player_wages": financial_data.player_wages,
                            "player_amortization": financial_data.player_amortization,
                            "other_staff_costs": financial_data.other_staff_costs,
                            "stadium_costs": financial_data.stadium_costs,
                            "administrative_expenses": financial_data.administrative_expenses,
                            "agent_fees": financial_data.agent_fees
                        },
                        "errors": [],
                        "warnings": []
                    })
                    
                    logger.info("Successfully extracted financial data", 
                               record_id=record_id,
                               extracted_fields=len([v for v in financial_data.__dict__.values() if v is not None]))
                    
                else:
                    # Handle insufficient text case
                    logger.warning("Insufficient text for extraction", 
                                 record_id=record_id,
                                 text_length=len(text_content))
                    
                    results.append({
                        "recordId": record_id,
                        "data": {
                            # Return null values for all fields when insufficient text
                            "revenue": None,
                            "turnover": None,
                            "total_assets": None,
                            "total_liabilities": None,
                            "net_assets": None,
                            "cash_at_bank": None,
                            "cash_and_cash_equivalents": None,
                            "creditors_due_within_one_year": None,
                            "creditors_due_after_one_year": None,
                            "operating_profit": None,
                            "profit_loss_before_tax": None,
                            "broadcasting_revenue": None,
                            "commercial_revenue": None,
                            "matchday_revenue": None,
                            "player_trading_income": None,
                            "player_wages": None,
                            "player_amortization": None,
                            "other_staff_costs": None,
                            "stadium_costs": None,
                            "administrative_expenses": None,
                            "agent_fees": None
                        },
                        "errors": [],
                        "warnings": [{"message": f"Insufficient text for extraction ({len(text_content)} chars)"}]
                    })
                    
            except Exception as e:
                logger.error("Financial extraction failed for record",
                           record_id=record_id,
                           error=str(e))
                
                results.append({
                    "recordId": record_id,
                    "data": {
                        # Return null values when extraction fails
                        "revenue": None,
                        "turnover": None,
                        "total_assets": None,
                        "total_liabilities": None,
                        "net_assets": None,
                        "cash_at_bank": None,
                        "cash_and_cash_equivalents": None,
                        "creditors_due_within_one_year": None,
                        "creditors_due_after_one_year": None,
                        "operating_profit": None,
                        "profit_loss_before_tax": None,
                        "broadcasting_revenue": None,
                        "commercial_revenue": None,
                        "matchday_revenue": None,
                        "player_trading_income": None,
                        "player_wages": None,
                        "player_amortization": None,
                        "other_staff_costs": None,
                        "stadium_costs": None,
                        "administrative_expenses": None,
                        "agent_fees": None
                    },
                    "errors": [{"message": f"Extraction failed: {str(e)}"}],
                    "warnings": []
                })
        
        logger.info("Completed financial extraction batch",
                   total_records=len(values),
                   successful_extractions=len([r for r in results if not r.get('errors')]))
        
        return {"values": results}
        
    except Exception as e:
        logger.error("Financial extraction skill failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/extract-financials-from-text-sections")
async def extract_financials_from_text_sections_skill(request_data: Dict[str, Any]):
    """
    Combine Document Intelligence text sections and extract financial data
    Works with existing index structure (no projections needed)
    """
    try:
        from app.api.endpoints.financial_extraction import extract_financial_metrics_with_gpt4
        
        values = request_data.get('values', [])
        results = []
        
        for record in values:
            record_id = record.get('recordId', '')
            text_sections = record.get('data', {}).get('text_sections', [])
            
            # Combine all text sections into one document
            combined_text = ""
            for section in text_sections:
                if hasattr(section, 'content'):
                    combined_text += section.content + "\n\n"
                elif isinstance(section, dict) and 'content' in section:
                    combined_text += section['content'] + "\n\n"
            
            # Extract financials from combined text
            if combined_text.strip():
                financial_data = await extract_financial_metrics_with_gpt4(combined_text)
                financial_dict = financial_data.dict()
                # Remove None values
                financial_dict = {k: v for k, v in financial_dict.items() if v is not None}
            else:
                financial_dict = {}
            
            results.append({
                "recordId": record_id,
                "data": financial_dict,
                "errors": [],
                "warnings": [] if financial_dict else [{"message": "No text content found"}]
            })
        
        return {"values": results}
        
    except Exception as e:
        logger.error("Financial extraction from sections failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))