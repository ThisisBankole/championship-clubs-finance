

import asyncio
from typing import Dict, Any, Optional
import structlog
from .client import DocumentIntelligenceService


logger = structlog.get_logger()

class ComprehensiveDocumentProcessor:
    """
    Orchestrates the complete document processing pipeline
    Combines Document Intelligence + Text Cleaning + Metadata + Financial Extraction
    """
    
    def __init__(self):
        self.doc_intelligence = DocumentIntelligenceService()
        
        # Import existing services
        from app.services.skillset.text_cleaner import TextCleaningService
        from app.services.skillset.metadata_extractor import ClubMetadataExtractor
        from app.api.endpoints.financial_extraction import extract_financial_metrics_with_gpt4
        
        self.text_cleaner = TextCleaningService()
        self.metadata_extractor = ClubMetadataExtractor()
        self.financial_extractor = extract_financial_metrics_with_gpt4
    
    async def process_document(self, file_data: bytes, blob_path: str, filename: str) -> Dict[str, Any]:
        """
        Complete document processing pipeline
        
        Args:
            file_data: Binary PDF content
            blob_path: Azure blob storage path for metadata extraction
            filename: Document filename for logging
            
        Returns:
            Dict with all fields needed by Azure AI Search indexer
        """
        
        logger.info("Starting comprehensive document processing",
                   filename=filename,
                   file_size=len(file_data))
        
        result = {
            # Initialize all expected outputs
            "cleaned_text": "",
            "text_quality_score": 0.0,
            "has_financial_content": False,
            "processing_method": "unknown",
            "tables_found": 0,
            "pages_processed": 0,
            "fallback_used": False,
            
            # Club metadata
            "company_number": None,
            "club_name": None,
            "accounts_year_end": None,
            
            # Financial data (21 fields)
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
        }
        
        try:
            # Step 1: Extract text using Document Intelligence with fallbacks
            logger.info("Step 1: Document Intelligence processing", filename=filename)
            
            raw_text, doc_metadata = await self.doc_intelligence.process_document_with_fallbacks(
                file_data, filename
            )
            
            result.update({
                "processing_method": doc_metadata.get("processing_method", "unknown"),
                "tables_found": doc_metadata.get("tables_found", 0),
                "pages_processed": doc_metadata.get("pages_processed", 0),
                "fallback_used": doc_metadata.get("fallback_used", False)
            })
            
            # Step 2: Enhanced text cleaning
            logger.info("Step 2: Text cleaning and enhancement", 
                       filename=filename,
                       raw_text_length=len(raw_text))
            
            if raw_text:
                # Apply additional cleaning beyond Document Intelligence
                cleaned_text = self.text_cleaner.clean_ocr_text(raw_text)
                
                # Calculate quality metrics
                quality_score = self.text_cleaner._calculate_text_quality(cleaned_text)
                has_financial_content = quality_score > 0.3
                
                result.update({
                    "cleaned_text": cleaned_text,
                    "text_quality_score": quality_score,
                    "has_financial_content": has_financial_content
                })
                
                logger.info("Text cleaning completed",
                           filename=filename,
                           cleaned_length=len(cleaned_text),
                           quality_score=quality_score)
            else:
                logger.warning("No text extracted from document", filename=filename)
            
            # Step 3: Extract club metadata from blob path
            logger.info("Step 3: Club metadata extraction", filename=filename)
            
            try:
                metadata = self.metadata_extractor.extract_from_blob_path(blob_path)
                result.update({
                    "company_number": metadata.get("company_number"),
                    "club_name": metadata.get("club_name"), 
                    "accounts_year_end": metadata.get("accounts_year_end")
                })
                
                logger.info("Metadata extraction completed",
                           filename=filename,
                           club_name=metadata.get("club_name"))
                           
            except Exception as e:
                logger.warning("Metadata extraction failed",
                              filename=filename,
                              error=str(e))
            
            # Step 4: Financial data extraction (only if we have good quality text)
            if result["has_financial_content"] and len(result["cleaned_text"]) > 500:
                logger.info("Step 4: Financial data extraction", filename=filename)
                
                try:
                    financial_data = await self.financial_extractor(result["cleaned_text"])
                    
                    # Update result with financial data
                    financial_fields = [
                        "is_abridged", "document_type", "profit_loss_filed",
                        "revenue", "turnover", "total_assets", "total_liabilities",
                        "net_assets", "cash_at_bank", "cash_and_cash_equivalents",
                        "creditors_due_within_one_year", "creditors_due_after_one_year",
                        "operating_profit", "profit_loss_before_tax", "broadcasting_revenue",
                        "commercial_revenue", "matchday_revenue", "player_trading_income",
                        "player_wages", "player_amortization", "other_staff_costs",
                        "stadium_costs", "administrative_expenses", "agent_fees"
                    ]
                    
                    extracted_count = 0
                    for field in financial_fields:
                        value = getattr(financial_data, field, None)
                        result[field] = value
                        if value is not None:
                            extracted_count += 1
                    
                    logger.info("Financial extraction completed",
                               filename=filename,
                               fields_extracted=extracted_count)
                               
                except Exception as e:
                    logger.error("Financial extraction failed",
                                filename=filename,
                                error=str(e))
            else:
                logger.info("Skipping financial extraction - insufficient quality text",
                           filename=filename,
                           has_financial_content=result["has_financial_content"],
                           text_length=len(result["cleaned_text"]))
            
            logger.info("Comprehensive processing completed successfully",
                       filename=filename,
                       quality_score=result["text_quality_score"],
                       financial_fields_populated=sum(1 for k, v in result.items() 
                                                     if k.endswith(('_revenue', '_profit', '_assets', '_liabilities', 
                                                                   'revenue', 'turnover', 'cash_at_bank')) and v is not None))
            
            return result
            
        except Exception as e:
            logger.error("Comprehensive processing failed",
                        filename=filename,
                        error=str(e))
            
            # Return partial result with error information
            result.update({
                "cleaned_text": f"Processing failed: {str(e)}",
                "text_quality_score": 0.0,
                "has_financial_content": False,
                "processing_method": "failed"
            })
            
            return result


# app/api/endpoints/comprehensive_skillset.py

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
                file_data_b64 = data.get('file_data', '')
                blob_path = data.get('blob_path', '') or data.get('metadata_storage_path', '')
                
                if not file_data_b64:
                    raise ValueError("No file_data provided")
                
                if not blob_path:
                    raise ValueError("No blob_path provided")
                
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
                    # All financial fields as None
                    **{field: None for field in [
                        "revenue", "turnover", "total_assets", "total_liabilities",
                        "net_assets", "cash_at_bank", "cash_and_cash_equivalents",
                        "creditors_due_within_one_year", "creditors_due_after_one_year",
                        "operating_profit", "profit_loss_before_tax", "broadcasting_revenue",
                        "commercial_revenue", "matchday_revenue", "player_trading_income",
                        "player_wages", "player_amortization", "other_staff_costs",
                        "stadium_costs", "administrative_expenses", "agent_fees"
                    ]}
                }
                
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