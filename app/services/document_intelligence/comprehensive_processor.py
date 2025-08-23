

import asyncio
from typing import Dict, Any, Optional
import structlog
from .client import DocumentIntelligenceService
from app.services.document_intelligence.super_robust_uk_extractor import SuperRobustUKFinancialExtractor

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
                print(f"\n🚀 STARTING FINANCIAL EXTRACTION FOR: {filename}")
                
                try:
           
        
                    # Create extractor instance
                    robust_extractor = SuperRobustUKFinancialExtractor()
                    
                    # Prepare sections for extraction
                    sections = {
                        'cleaned_text': result["cleaned_text"],
                        'profit_loss': result["cleaned_text"],
                        'balance_sheet': result["cleaned_text"],
                    }
                    
                    # Extract using robust pattern matching
                    financial_data = robust_extractor.extract_all_fields(sections)
                    
                    print(f"DEBUG - Robust extractor found {len([v for v in financial_data.values() if v is not None])} fields")
                    
                    # Update result with financial data
                    financial_fields = [
                        "is_abridged", "document_type", "profit_loss_filed",
                        "revenue", "turnover", "total_assets", "total_liabilities",
                        "net_assets", "cash_at_bank", "cash_and_cash_equivalents",
                        "creditors_due_within_one_year", "creditors_due_after_one_year",
                        "operating_profit", "profit_loss_before_tax", "broadcasting_revenue",
                        "commercial_revenue", "matchday_revenue", "player_trading_income",
                        "player_wages", "player_amortization", "other_staff_costs",
                        "stadium_costs", "administrative_expenses", "agent_fees",  "net_income", "total_equity",
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
                        value = financial_data.get(field)
                        result[field] = value
                        if value is not None:
                            extracted_count += 1
                            
                    if financial_data.get('turnover') and not result.get('revenue'):
                        result['revenue'] = financial_data['turnover']
                               
                               
                    print(f"DEBUG - Key extractions:")
                    print(f"  turnover: {result.get('turnover'):,}" if result.get('turnover') else "  turnover: None")
                    print(f"  admin_expenses: {result.get('administrative_expenses'):,}" if result.get('administrative_expenses') else "  admin_expenses: None")
                    print(f"  cost_of_sales: {result.get('cost_of_sales'):,}" if result.get('cost_of_sales') else "  cost_of_sales: None")
                    print(f"  player_amortization: {result.get('player_amortization'):,}" if result.get('player_amortization') else "  player_amortization: None")
                    
                    logger.info("Enhanced robust extraction completed",
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


    def validate_extracted_data(self, financial_data, club_name):
        """
        Validate the extracted financial data for accuracy and consistency
        Returns validation status and list of issues found
        """
        
        print(f"\n🔍 VALIDATING DATA FOR: {club_name}")
        print("=" * 50)
    
        issues = []
        
        # Check 1: Balance Sheet Equation (Total Assets = Total Liabilities + Total Equity)
        if all(hasattr(financial_data, attr) and getattr(financial_data, attr) is not None 
            for attr in ['total_assets', 'total_liabilities', 'total_equity']):
            
            left_side = financial_data.total_assets
            right_side = financial_data.total_liabilities + financial_data.total_equity
            difference = abs(left_side - right_side)
            
            print(f"📊 BALANCE SHEET CHECK:")
            print(f"   Total Assets: {left_side:,}")
            print(f"   Total Liabilities: {financial_data.total_liabilities:,}")
            print(f"   Total Equity: {financial_data.total_equity:,}")
            print(f"   Right Side (Liab + Equity): {right_side:,}")
            print(f"   Difference: {difference:,}")
            
            if difference > 1000:  # Allow £1k tolerance for rounding
                issue = f"Balance sheet equation fails: Assets {left_side:,} ≠ Liabilities {financial_data.total_liabilities:,} + Equity {financial_data.total_equity:,} = {right_side:,} (diff: {difference:,})"
                issues.append(issue)
                print(f"   ❌ FAILED: {issue}")
            else:
                print(f"   ✅ PASSED: Balance sheet equation checks out")
                
        else:
            print(f"   ⚠️  SKIPPED: Missing balance sheet data")
        
        # Check 2: Revenue Breakdown Should Approximately Equal Total Revenue
        if financial_data.turnover and financial_data.turnover > 0:
            revenue_components = sum(filter(None, [
                financial_data.matchday_revenue,
                financial_data.broadcasting_revenue, 
                financial_data.commercial_revenue
            ]))
            
            print(f"\n💰 REVENUE BREAKDOWN CHECK:")
            print(f"   Total Revenue: {financial_data.turnover:,}")
            print(f"   Matchday: {financial_data.matchday_revenue or 0:,}")
            print(f"   Broadcasting: {financial_data.broadcasting_revenue or 0:,}")
            print(f"   Commercial: {financial_data.commercial_revenue or 0:,}")
            print(f"   Component Sum: {revenue_components:,}")
            
            if revenue_components > 0:
                percentage_diff = abs(revenue_components - financial_data.turnover) / financial_data.turnover
                
                print(f"   Percentage Difference: {percentage_diff:.1%}")
                 
                
                if percentage_diff > 0.15:  # More than 15% difference
                    issues.append(f"Revenue breakdown mismatch: Components {revenue_components:,} vs Total {financial_data.turnover:,} (diff: {percentage_diff:.1%})")
        
        # Check 3: Asset Components Should Add Up to Total Assets
        if all(hasattr(financial_data, attr) and getattr(financial_data, attr) is not None 
            for attr in ['intangible_assets', 'tangible_assets', 'current_assets']):
            
            calculated_assets = financial_data.intangible_assets + financial_data.tangible_assets + financial_data.current_assets
            
            print(f"\n🏢 ASSET COMPONENTS CHECK:")
            print(f"   Intangible Assets: {financial_data.intangible_assets:,}")
            print(f"   Tangible Assets: {financial_data.tangible_assets:,}")
            print(f"   Current Assets: {financial_data.current_assets:,}")
            print(f"   Calculated Total: {calculated_assets:,}")
            print(f"   Reported Total: {financial_data.total_assets or 'NULL':,}")
            
            if financial_data.total_assets and abs(calculated_assets - financial_data.total_assets) > 1000:
                issue = f"Asset components don't match total: Calculated {calculated_assets:,} vs Reported {financial_data.total_assets:,}"
                issues.append(issue)
                print(f"   ❌ FAILED: {issue}")
            else:
                print(f"   ✅ PASSED: Asset components match total")
                
        else:
            print(f"   ⚠️  SKIPPED: Missing asset component data")
        
        # Check 4: Creditors Should Be Negative Values
        for field in ['creditors_due_within_one_year', 'creditors_due_after_one_year']:
            value = getattr(financial_data, field, None)
            if value is not None and value > 0:
                issues.append(f"{field} should be negative but got positive value: {value:,}")
        
        # Check 5: Net Assets vs Total Equity Consistency
        if (financial_data.net_assets is not None and financial_data.total_equity is not None 
            and abs(financial_data.net_assets - financial_data.total_equity) > 1000):
            issues.append(f"Net assets {financial_data.net_assets:,} doesn't match total equity {financial_data.total_equity:,}")
        
        # Check 6: Reasonable Revenue Values (basic sanity check)
        if financial_data.turnover is not None:
            if financial_data.turnover < 100000:  # Less than £100k seems too low
                issues.append(f"Revenue seems unusually low: {financial_data.turnover:,} - check for scale issues")
            elif financial_data.turnover > 1000000000:  # More than £1B seems too high for Championship
                issues.append(f"Revenue seems unusually high: {financial_data.turnover:,} - check for scale issues")
        
        return len(issues) == 0, issues

