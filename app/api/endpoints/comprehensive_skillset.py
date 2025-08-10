from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import structlog
import base64

from app.services.document_intelligence.comprehensive_processor import ComprehensiveDocumentProcessor

logger = structlog.get_logger()
router = APIRouter()

@router.post("/comprehensive-document-processor")
async def comprehensive_document_processor_skill(request_data: Dict[str, Any]):
    """
    Azure AI Search Custom Web API Skill
    Complete document processing: Document Intelligence + Text Cleaning + Metadata + Financial Extraction
    
    Input: Raw PDF from Azure AI Search
    Output: All fields needed for indexing
    """
    
    try:
        processor = ComprehensiveDocumentProcessor()
        values = request_data.get('values', [])
        results = []
        
        for record in values:
            record_id = record.get('recordId', '')
            data = record.get('data', {})
            
            logger.info("Processing comprehensive document request",
                       record_id=record_id,
                       available_fields=list(data.keys()))
            
            try:
                # Extract file data and metadata
                file_data_raw = data.get('file_data', '')
                blob_path = data.get('blob_path', '') or data.get('metadata_storage_path', '')

                if not file_data_raw:
                    raise ValueError("No file_data provided")

                if not blob_path:
                    raise ValueError("No blob_path provided")

                # Handle different Azure AI Search file_data formats
                logger.info("Debug file_data format", 
                        record_id=record_id,
                        file_data_type=type(file_data_raw),
                        has_type_field=isinstance(file_data_raw, dict) and '$type' in file_data_raw,
                        dict_keys=list(file_data_raw.keys()) if isinstance(file_data_raw, dict) else None)

                if isinstance(file_data_raw, dict):
                    # Azure AI Search sometimes sends file_data as dict with '$type' and 'data'
                    if '$type' in file_data_raw and 'data' in file_data_raw:
                        file_data_b64 = file_data_raw['data']
                    elif 'data' in file_data_raw:
                        file_data_b64 = file_data_raw['data']
                    else:
                        raise ValueError(f"file_data dict format not recognized. Keys: {list(file_data_raw.keys())}")
                elif isinstance(file_data_raw, str):
                    # Standard base64 string format
                    file_data_b64 = file_data_raw
                else:
                    raise ValueError(f"file_data format not supported: {type(file_data_raw)}")

                # Decode base64 file data
                try:
                    file_data = base64.b64decode(file_data_b64)
                except Exception as e:
                    raise ValueError(f"Failed to decode file_data: {str(e)}")
                
                # Extract filename from blob path
                filename = blob_path.split('/')[-1] if '/' in blob_path else blob_path
                
                logger.info("Starting comprehensive processing",
                           record_id=record_id,
                           filename=filename,
                           file_size=len(file_data),
                           blob_path=blob_path)
                
                # Process document through complete pipeline
                processing_result = await processor.process_document(
                    file_data=file_data,
                    blob_path=blob_path,
                    filename=filename
                )
                
                # Return all fields in Azure AI Search Web API skill format
                results.append({
                    "recordId": record_id,
                    "data": processing_result,
                    "errors": [],
                    "warnings": []
                })
                
                logger.info("Comprehensive processing completed successfully",
                           record_id=record_id,
                           filename=filename,
                           quality_score=processing_result.get("text_quality_score", 0),
                           method=processing_result.get("processing_method", "unknown"))
                
            except Exception as e:
                logger.error("Comprehensive processing failed for record",
                           record_id=record_id,
                           error=str(e))
                
                # Return error result with empty data structure
                error_result = {
                    "cleaned_text": "",
                    "text_quality_score": 0.0,
                    "has_financial_content": False,
                    "processing_method": "error",
                    "tables_found": 0,
                    "pages_processed": 0,
                    "fallback_used": False,
                    "company_number": None,
                    "club_name": None,
                    "accounts_year_end": None,
                }
                
                # Add all financial fields as None
                financial_fields = [
                    "revenue", "turnover", "total_assets", "total_liabilities",
                    "net_assets", "cash_at_bank", "cash_and_cash_equivalents",
                    "creditors_due_within_one_year", "creditors_due_after_one_year",
                    "operating_profit", "profit_loss_before_tax", "broadcasting_revenue",
                    "commercial_revenue", "matchday_revenue", "player_trading_income",
                    "player_wages", "player_amortization", "other_staff_costs",
                    "stadium_costs", "administrative_expenses", "agent_fees"
                ]
                
                for field in financial_fields:
                    error_result[field] = None
                
                results.append({
                    "recordId": record_id,
                    "data": error_result,
                    "errors": [{"message": f"Processing failed: {str(e)}"}],
                    "warnings": []
                })
        
        logger.info("Completed comprehensive processing batch",
                   total_records=len(values),
                   successful_records=len([r for r in results if not r.get('errors')]))
        
        return {"values": results}
        
    except Exception as e:
        logger.error("Comprehensive document processor skill failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-comprehensive-processing")
async def test_comprehensive_processing(file_path: str):
    """
    Test endpoint for comprehensive document processing
    """
    try:
        import os
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Create test blob path
        blob_path = f"test-container/company_12345678/club_test/2023/{os.path.basename(file_path)}"
        filename = os.path.basename(file_path)
        
        # Process document
        processor = ComprehensiveDocumentProcessor()
        result = await processor.process_document(
            file_data=file_data,
            blob_path=blob_path,
            filename=filename
        )
        
        return {
            "filename": filename,
            "file_size": len(file_data),
            "processing_result": result
        }
        
    except Exception as e:
        logger.error("Test comprehensive processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))