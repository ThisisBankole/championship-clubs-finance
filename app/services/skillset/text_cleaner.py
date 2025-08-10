
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
        FIXED: Proper Web API skill response format for Azure AI Search
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
                data.get('content', []) or
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
                    
                    # FIXED: Proper Web API skill format with flat output
                    results.append({
                        "recordId": record_id,
                        "data": {
                            "cleaned_text": "",  # Always provide the expected output field
                            "text_quality_score": 0.0,
                            "sections_processed": 0,
                            "has_financial_content": False
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
                
                # Calculate text quality metrics
                quality_score = self._calculate_text_quality(cleaned_text)
            
                # FIXED: Return flat fields that match skillset output expectations
                result = {
                    "recordId": record_id,
                    "data": {
                        # PRIMARY OUTPUT: This is what the financial extraction skill needs
                        "cleaned_text": cleaned_text,
                        
                        # SECONDARY OUTPUTS: Useful metadata for monitoring
                        "text_quality_score": quality_score,
                        "sections_processed": len([s for s in text_sections if len(str(s).strip()) > 10]),
                        "original_text_length": len(combined_text),
                        "cleaned_text_length": len(cleaned_text),
                        
                        # BOOLEAN FLAGS: Easy filtering/monitoring in index
                        "has_financial_content": quality_score > 0.3,
                        "has_income_statement": sections.get("has_income_statement", False),
                        "has_balance_sheet": sections.get("has_balance_sheet", False),
                        "has_cash_flow": sections.get("has_cash_flow", False),
                        "has_directors_report": sections.get("has_directors_report", False),
                        
                        # PREVIEW: For debugging and validation
                        "text_preview": cleaned_text[:500] if cleaned_text else ""
                    },
                    "errors": [],
                    "warnings": []
                }
            
                # Add warnings for potential issues (but not errors)
                if len(cleaned_text) < 200:
                    result["warnings"].append({
                        "message": f"Very little text extracted ({len(cleaned_text)} chars)"
                    })
                
                if quality_score < 0.2:
                    result["warnings"].append({
                        "message": f"Low text quality score: {quality_score:.2f}"
                    })
                
                if not any(sections.values()):
                    result["warnings"].append({
                        "message": "No recognizable financial statement sections found"
                    })
                
                results.append(result)
                
                logger.info("Successfully processed text cleaning",
                           record_id=record_id,
                           text_length=len(cleaned_text),
                           quality_score=quality_score,
                           has_financial_sections=any(sections.values()))
            
            except Exception as e:
                logger.error("Text cleaning failed for record",
                           record_id=record_id,
                           error=str(e))
                
                # FIXED: Return proper error format
                results.append({
                    "recordId": record_id,
                    "data": {
                        "cleaned_text": "",  # Always provide expected output field
                        "text_quality_score": 0.0,
                        "sections_processed": 0,
                        "has_financial_content": False
                    },
                    "errors": [{"message": f"Text cleaning failed: {str(e)}"}],
                    "warnings": []
                })
    
        logger.info("Completed text cleaning batch",
                   total_records=len(values),
                   successful_records=len([r for r in results if not r.get('errors')]))
        
        return {"values": results}

    def _calculate_text_quality(self, text: str) -> float:
        """
        Calculate a quality score for the cleaned text (0.0 to 1.0)
        Higher scores indicate better financial content
        """
        if not text:
            return 0.0
        
        score = 0.0
        
        # Financial keywords presence (0.0 to 0.4)
        financial_keywords = [
            'turnover', 'revenue', 'profit', 'loss', 'assets', 'liabilities',
            'cash', 'bank', 'creditors', 'broadcasting', 'commercial', 'matchday',
            'player', 'wages', 'stadium', 'balance sheet', 'income statement'
        ]
        
        text_lower = text.lower()
        keyword_matches = sum(1 for keyword in financial_keywords if keyword in text_lower)
        score += min(keyword_matches / len(financial_keywords), 0.4)
        
        # Number presence (0.0 to 0.3)
        number_patterns = len(re.findall(r'£?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?', text))
        score += min(number_patterns / 20, 0.3)  # Normalize to max 0.3
        
        # Text structure (0.0 to 0.3)
        has_proper_sections = any(section in text_lower for section in 
                                 ['balance sheet', 'profit and loss', 'cash flow'])
        if has_proper_sections:
            score += 0.3
        
        return min(score, 1.0)