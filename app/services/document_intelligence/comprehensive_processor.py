

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
            "operating_expenses": None, 
            "net_income": None, 
            "total_equity": None,
            "administrative_expenses": None,
            "agent_fees": None,
            "cost_of_sales": None,
            "gross_profit": None,
            "gross_loss": None,
            "interest_receivable": None,
            "interest_payable": None,
            "other_operating_income": None,
            "staff_costs_total": None,
            "social_security_costs": None,
            "pension_costs": None,
            "depreciation_charges": None,
            "operating_lease_charges": None,
            "profit_on_player_disposals": None,
            "loss_on_player_disposals": None,
            "intangible_assets": None,
            "tangible_assets": None,
            "current_assets": None,
            "stocks": None,
            "debtors": None,
            "operating_cash_flow": None,
            "investing_cash_flow": None,
            "financing_cash_flow": None
            
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
                    print(f"DEBUG - ComprehensiveProcessor: operating_expenses = {getattr(financial_data, 'operating_expenses', None)}")
                    print(f"DEBUG - ComprehensiveProcessor: net_income = {getattr(financial_data, 'net_income', None)}")
                    print(f"DEBUG - ComprehensiveProcessor: total_equity = {getattr(financial_data, 'total_equity', None)}")
                    
                    # Update result with financial data
                    financial_fields = [
                        "is_abridged", "document_type", "profit_loss_filed",
                        "revenue", "turnover", "total_assets", "total_liabilities",
                        "net_assets", "cash_at_bank", "cash_and_cash_equivalents",
                        "creditors_due_within_one_year", "creditors_due_after_one_year",
                        "operating_profit", "profit_loss_before_tax", "broadcasting_revenue",
                        "commercial_revenue", "matchday_revenue", "player_trading_income",
                        "player_wages", "player_amortization", "other_staff_costs",
                        "stadium_costs", "administrative_expenses", "agent_fees", "operating_expenses", "net_income", "total_equity",
                        "cost_of_sales", "gross_profit", "gross_loss",
                        "interest_receivable", "interest_payable", "other_operating_income",
                        "staff_costs_total", "social_security_costs", "pension_costs",
                        "depreciation_charges", "operating_lease_charges",
                        "profit_on_player_disposals", "loss_on_player_disposals",
                        "intangible_assets", "tangible_assets", "current_assets",
                        "stocks", "debtors", "operating_cash_flow",
                        "investing_cash_flow", "financing_cash_flow"
                    ]
                    
                    extracted_count = 0
                    for field in financial_fields:
                        value = getattr(financial_data, field, None)
                        result[field] = value
                        if value is not None:
                            extracted_count += 1
                            
                    print(f"DEBUG - ComprehensiveProcessor result: operating_expenses = {result.get('operating_expenses')}")
                    print(f"DEBUG - ComprehensiveProcessor result: net_income = {result.get('net_income')}")
                    print(f"DEBUG - ComprehensiveProcessor result: total_equity = {result.get('total_equity')}")
                    
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


