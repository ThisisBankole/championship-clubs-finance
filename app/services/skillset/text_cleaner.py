
import json
import re
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

class TextCleaningService:
    """Service for cleaning OCR text from financial documents"""
    
    def clean_ocr_text(self, text: str) -> str:
        """
        Comprehensive OCR text cleaning for financial documents
        Fixes common issues that prevent financial extraction
        """
        if not text:
            return ""
        
        # Apply cleaning in sequence
        text = self._fix_number_formatting(text)
        text = self._fix_financial_labels(text)
        text = self._fix_ocr_artifacts(text)
        text = self._clean_whitespace(text)
        
        return text.strip()
    
    def _fix_number_formatting(self, text: str) -> str:
        """Fix common number formatting issues in OCR text"""
        
        # Fix concatenated parentheses: "123,456(" -> "123,456 ("
        text = re.sub(r'(\d)\(', r'\1 (', text)
        
        # ONLY add space after £ when there's no space, but don't break existing formatting
        # This fixes "£28.2m" -> "£ 28.2m" but should preserve decimals and 'm'
        # Let's be more conservative and only fix obvious cases
        
        return text
    
    def _fix_financial_labels(self, text: str) -> str:
        """Fix concatenated financial labels with numbers"""
        
        # Common financial terms that get stuck to numbers in OCR
        financial_terms = [
            'Turnover', 'Revenue', 'Cash at bank', 'Net assets', 'Total assets',
            'Creditors', 'Profit', 'Loss', 'Tax', 'Interest', 'Broadcasting',
            'Commercial', 'Matchday', 'Player', 'Wages', 'Stadium', 'Operating',
            'EBITDA', 'Amortisation', 'Depreciation', 'Dividend', 'Capital',
            'Current assets', 'Fixed assets', 'Current liabilities'
        ]
        
        for term in financial_terms:
            # Fix: "Turnover28.2m" -> "Turnover 28.2m"
            pattern = f'({re.escape(term)})(\d)'
            text = re.sub(pattern, r'\1 \2', text, flags=re.IGNORECASE)
            
            # Fix: "28.2mTurnover" -> "28.2m Turnover"  
            pattern = f'(\d)({re.escape(term)})'
            text = re.sub(pattern, r'\1 \2', text, flags=re.IGNORECASE)
        
        return text
    
    def _fix_ocr_artifacts(self, text: str) -> str:
        """Fix common OCR scanning artifacts"""
        
        # Remove common header/footer artifacts
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\*{3,}', '', text)  # Remove separator lines
        text = re.sub(r'[-]{3,}', '', text)  # Remove dash lines
        
        # Fix common OCR character substitutions (only in text context)
        # Be careful not to change numbers
        text = re.sub(r'([a-zA-Z])\|([a-zA-Z])', r'\1I\2', text)  # Pipe -> I
        text = re.sub(r'([a-zA-Z])§([a-zA-Z])', r'\1S\2', text)    # Section -> S
        
        return text
    
    def _clean_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace and formatting"""
        
        # Remove excessive newlines (more than 2)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove excessive spaces (3 or more)
        text = re.sub(r' {3,}', ' ', text)
        
        # Don't fix spacing around punctuation as it breaks financial numbers
        
        return text
    
    def _extract_sections(self, text: str) -> Dict[str, bool]:
        """Identify key financial statement sections in the document"""
        
        return {
            "has_income_statement": bool(re.search(
                r'(STATEMENT OF COMPREHENSIVE INCOME|PROFIT AND LOSS|INCOME STATEMENT)', 
                text, re.IGNORECASE
            )),
            "has_balance_sheet": bool(re.search(
                r'BALANCE SHEET', text, re.IGNORECASE
            )),
            "has_cash_flow": bool(re.search(
                r'(CASH FLOW|STATEMENT OF CASH)', text, re.IGNORECASE
            )),
            "has_directors_report": bool(re.search(
                r'DIRECTORS.{0,10}REPORT', text, re.IGNORECASE
            ))
        }
    
    def extract_text_from_json_sections(self, text_sections: List[str]) -> str:
        """
        Extract text content from JSON-formatted text sections
        This handles your specific issue where text_sections_content contains JSON strings
        """
        combined_text = ""
        section_count = 0
        
        for section in text_sections:
            try:
                # Parse JSON string from Azure Search
                if isinstance(section, str):
                    section_data = json.loads(section)
                    content = section_data.get('content', '')
                    
                    # Filter out mostly empty sections
                    if content and len(content.strip()) > 10:
                        # Check content quality - skip sections that are mostly whitespace
                        non_whitespace_chars = len(content.replace('\n', '').replace(' ', '').replace('\t', ''))
                        total_chars = len(content)
                        
                        if total_chars > 0 and (non_whitespace_chars / total_chars) > 0.1:  # At least 10% actual content
                            combined_text += content + "\n\n"
                            section_count += 1
                            
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                if isinstance(section, str) and len(section.strip()) > 10:
                    combined_text += section + "\n\n"
                    section_count += 1
        
        logger.info("Extracted text from sections", 
                   sections_processed=section_count,
                   text_length=len(combined_text))
        
        return combined_text
    
    def process_azure_search_request(self, request_data: Dict) -> Dict:
        """
        Process Azure AI Search skillset request format
        Transforms JSON text sections into clean, readable text
        """
        values = request_data.get('values', [])
        results = []
        
        for record in values:
            record_id = record.get('recordId', '')
            data = record.get('data', {})
            
            # Try multiple possible field names from Azure Search
            text_sections = (
                data.get('text_sections_content', []) or 
                data.get('text_sections', []) or
                data.get('text', []) or
                []
            )
            
            logger.info("Processing text cleaning request", 
                       record_id=record_id,
                       available_fields=list(data.keys()),
                       text_sections_count=len(text_sections))
            
            try:
                # If no text sections, return empty result (no errors)
                if not text_sections:
                    logger.warning("No text sections found", 
                                 record_id=record_id,
                                 available_fields=list(data.keys()))
                    
                    results.append({
                        "recordId": record_id,
                        "data": {
                            "cleaned_text": "",
                            "preview": "",
                            "summary": {
                                "total_sections_processed": 0,
                                "text_length": 0,
                                "has_income_statement": False,
                                "has_balance_sheet": False,
                                "has_cash_flow": False,
                                "has_directors_report": False,
                                "error": f"No text in fields: {list(data.keys())}"
                            }
                        },
                        "errors": [],  # No errors - just empty data
                        "warnings": [{"message": f"No text content in available fields: {list(data.keys())}"}]
                    })
                    continue
                
                # Extract text from JSON sections
                combined_text = self.extract_text_from_json_sections(text_sections)
                
                # Clean the extracted text
                cleaned_text = self.clean_ocr_text(combined_text)
                
                # Analyze document structure
                sections = self._extract_sections(cleaned_text)
                
                # Create processing summary
                summary = {
                    "total_sections_processed": len([s for s in text_sections if len(str(s).strip()) > 10]),
                    "text_length": len(cleaned_text),
                    **sections
                }
                
                # Prepare successful result
                result = {
                    "recordId": record_id,
                    "data": {
                        "cleaned_text": cleaned_text,
                        "preview": cleaned_text[:1000] if cleaned_text else "",
                        "summary": summary
                    },
                    "errors": [],
                    "warnings": []
                }
                
                # Add warnings for potential issues (but not errors)
                if len(cleaned_text) < 100:
                    result["warnings"].append({
                        "message": f"Very little text extracted ({len(cleaned_text)} chars)"
                    })
                
                if not any(sections.values()):
                    result["warnings"].append({
                        "message": "No recognizable financial statement sections found"
                    })
                
                results.append(result)
                
                logger.info("Successfully processed text cleaning",
                           record_id=record_id,
                           text_length=len(cleaned_text),
                           has_financial_sections=any(sections.values()))
                
            except Exception as e:
                logger.error("Text cleaning failed for record",
                           record_id=record_id,
                           error=str(e))
                
                # Return error result (no data when there's an error)
                results.append({
                    "recordId": record_id,
                    "data": {},  # Empty data object when there's an error
                    "errors": [{"message": f"Text cleaning failed: {str(e)}"}],
                    "warnings": []
                })
        
        logger.info("Completed text cleaning batch",
                   total_records=len(values),
                   successful_records=len([r for r in results if not r.get('errors')]))
        
        return {"values": results}