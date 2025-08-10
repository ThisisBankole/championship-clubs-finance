

import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
import structlog
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

logger = structlog.get_logger()

class DocumentIntelligenceService:
    """
    Document Intelligence service with RAG-style fallback strategy
    """
    
    def __init__(self):
        self.endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        self.key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
        
        if not self.endpoint or not self.key:
            raise ValueError("Azure Document Intelligence endpoint and key must be configured")
        
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )
        
    async def process_document_with_fallbacks(self, file_data: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process document using RAG fallback strategy:
        1. Try prebuilt-layout with markdown (advanced)
        2. Try prebuilt-read (reliable fallback)
        3. Extract basic text (emergency fallback)
        
        Returns: (cleaned_text, processing_metadata)
        """
        
        processing_metadata = {
            "filename": filename,
            "file_size": len(file_data),
            "processing_method": None,
            "tables_found": 0,
            "pages_processed": 0,
            "fallback_used": False,
            "quality_score": 0.0
        }
        
        # Primary Strategy: prebuilt-layout with advanced processing
        try:
            logger.info("Attempting primary processing with prebuilt-layout", filename=filename)
            
            result = await self._call_document_intelligence(
                file_data, 
                model="prebuilt-layout",
                output_format="markdown"
            )
            
            cleaned_text, metadata = self._process_layout_result(result)
            
            processing_metadata.update({
                "processing_method": "prebuilt-layout",
                "tables_found": metadata.get("tables_count", 0),
                "pages_processed": metadata.get("pages_count", 0),
                "quality_score": metadata.get("quality_score", 0.0)
            })
            
            logger.info("Primary processing successful", 
                       filename=filename,
                       text_length=len(cleaned_text),
                       tables_found=metadata.get("tables_count", 0))
            
            return cleaned_text, processing_metadata
            
        except Exception as e:
            logger.warning("Primary processing failed, trying fallback",
                          filename=filename,
                          error=str(e))
            
            processing_metadata["fallback_used"] = True
        
        # Fallback Strategy: prebuilt-read
        try:
            logger.info("Attempting fallback processing with prebuilt-read", filename=filename)
            
            result = await self._call_document_intelligence(
                file_data,
                model="prebuilt-read",
                output_format="text"
            )
            
            cleaned_text = self._process_read_result(result)
            
            processing_metadata.update({
                "processing_method": "prebuilt-read",
                "pages_processed": 1,
                "quality_score": 0.5  # Lower quality score for fallback
            })
            
            logger.info("Fallback processing successful",
                       filename=filename,
                       text_length=len(cleaned_text))
            
            return cleaned_text, processing_metadata
            
        except Exception as e:
            logger.error("All Document Intelligence processing failed",
                        filename=filename,
                        error=str(e))
            
            # Emergency fallback: return empty but valid result
            processing_metadata.update({
                "processing_method": "failed",
                "quality_score": 0.0
            })
            
            return "", processing_metadata
    
    async def _call_document_intelligence(self, file_data: bytes, model: str, output_format: str):
        """Call Document Intelligence API with specified model"""
        
        try:
            # Create analyze request
            analyze_request = AnalyzeDocumentRequest(bytes_source=file_data)
            
            # Start analysis
            poller = self.client.begin_analyze_document(
                model_id=model,
                body=file_data,
                content_type="application/pdf",
                output_content_format=output_format
            )
            
            # Wait for completion (with timeout)
            result = poller.result()
            return result
            
        except HttpResponseError as e:
            logger.error("Document Intelligence API error",
                        model=model,
                        status_code=e.status_code,
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Document Intelligence processing error",
                        model=model,
                        error=str(e))
            raise
    
    def _process_layout_result(self, result) -> Tuple[str, Dict[str, Any]]:
        """
        Process prebuilt-layout result with RAG-style enhancements
        """
        
        metadata = {
            "tables_count": len(result.tables) if result.tables else 0,
            "pages_count": len(result.pages) if result.pages else 0,
            "paragraphs_count": len(result.paragraphs) if result.paragraphs else 0
        }
        
        # Extract and filter paragraphs (RAG strategy)
        relevant_paragraphs = []
        excluded_roles = ["pageHeader", "pageFooter", "footnote", "pageNumber"]
        
        if result.paragraphs:
            for paragraph in result.paragraphs:
                # Check if paragraph has a role and if it should be excluded
                if hasattr(paragraph, 'role') and paragraph.role in excluded_roles:
                    continue
                relevant_paragraphs.append(paragraph)
        
        # Format tables for better LLM comprehension (RAG strategy)
        formatted_content = []
        
        if result.tables:
            formatted_tables = self._format_tables_for_llm(result.tables)
            formatted_content.extend(formatted_tables)
        
        # Add paragraph content
        for paragraph in relevant_paragraphs:
            if hasattr(paragraph, 'content') and paragraph.content:
                formatted_content.append(paragraph.content)
        
        # Combine and clean content
        combined_text = "\n\n".join(formatted_content)
        cleaned_text = self._clean_extracted_content(combined_text)
        
        # Calculate quality score
        metadata["quality_score"] = self._calculate_content_quality(cleaned_text)
        
        return cleaned_text, metadata
    
    def _process_read_result(self, result) -> str:
        """Process prebuilt-read result (simpler fallback)"""
        
        if hasattr(result, 'content') and result.content:
            cleaned_text = self._clean_extracted_content(result.content)
            return cleaned_text
        
        return ""
    
    def _format_tables_for_llm(self, tables) -> List[str]:
        """
        Format tables in RAG-style readable format
        Example: "Name: Alice, Age: 25 \nName: Bob, Age: 32"
        """
        
        formatted_tables = []
        
        for table in tables:
            if not hasattr(table, 'cells') or not table.cells:
                continue
                
            # Group cells by row
            rows = {}
            headers = []
            
            for cell in table.cells:
                row_index = cell.row_index
                col_index = cell.column_index
                content = cell.content if hasattr(cell, 'content') else ""
                
                if row_index not in rows:
                    rows[row_index] = {}
                rows[row_index][col_index] = content
                
                # Collect headers from first row
                if row_index == 0:
                    headers.append((col_index, content))
            
            # Sort headers by column index
            headers.sort(key=lambda x: x[0])
            header_names = [header[1] for header in headers]
            
            # Format table rows
            table_lines = []
            for row_index in sorted(rows.keys()):
                if row_index == 0:  # Skip header row
                    continue
                    
                row_data = rows[row_index]
                row_pairs = []
                
                for col_index, header in enumerate(header_names):
                    if col_index in row_data and row_data[col_index]:
                        row_pairs.append(f"{header}: {row_data[col_index]}")
                
                if row_pairs:
                    table_lines.append(", ".join(row_pairs))
            
            if table_lines:
                formatted_table = "\n".join(table_lines)
                formatted_tables.append(f"Table Data:\n{formatted_table}")
        
        return formatted_tables
    
    def _clean_extracted_content(self, content: str) -> str:
        """Clean extracted content (reuse existing text cleaning logic)"""
        
        if not content:
            return ""
        
        # Basic cleaning
        import re
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common artifacts
        content = re.sub(r'Page \d+ of \d+', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\*{3,}', '', content)
        content = re.sub(r'[-]{3,}', '', content)
        
        # Fix common OCR issues
        content = re.sub(r'(\d)\(', r'\1 (', content)  # Fix concatenated parentheses
        content = re.sub(r'£(\d)', r'£ \1', content)   # Fix currency formatting
        
        return content.strip()
    
    def _calculate_content_quality(self, content: str) -> float:
        """Calculate content quality score (0.0 to 1.0)"""
        
        if not content:
            return 0.0
        
        score = 0.0
        
        # Financial keywords presence (0.0 to 0.4)
        financial_keywords = [
            'turnover', 'revenue', 'profit', 'loss', 'assets', 'liabilities',
            'cash', 'bank', 'creditors', 'broadcasting', 'commercial', 'matchday',
            'player', 'wages', 'stadium', 'balance sheet', 'income statement'
        ]
        
        content_lower = content.lower()
        keyword_matches = sum(1 for keyword in financial_keywords if keyword in content_lower)
        score += min(keyword_matches / len(financial_keywords), 0.4)
        
        # Number presence (0.0 to 0.3)
        import re
        number_patterns = len(re.findall(r'£?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?', content))
        score += min(number_patterns / 20, 0.3)
        
        # Text structure (0.0 to 0.3)
        has_proper_sections = any(section in content_lower for section in 
                                 ['balance sheet', 'profit and loss', 'cash flow'])
        if has_proper_sections:
            score += 0.3
        
        return min(score, 1.0)