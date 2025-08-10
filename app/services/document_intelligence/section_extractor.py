import re
from typing import Dict, Any, Optional, List, Tuple
import structlog

from app.config.document_types.uk_football_financials import UK_FOOTBALL_FINANCIAL_CONFIG

logger = structlog.get_logger()

class FinancialSectionExtractor:
    """
    Extracts specific sections from UK football club financial statements
    """
    
    def __init__(self):
        self.config = UK_FOOTBALL_FINANCIAL_CONFIG
        self.section_config = self.config["document_structure"]["section_identifiers"]
        
    def extract_all_sections(self, text: str) -> Dict[str, str]:
        """
        Extract all major sections from the financial statement
        
        Returns:
            Dict with keys: 'profit_loss', 'balance_sheet', 'notes', 'cash_flow'
        """
        sections = {}
        
        # Extract each major section
        sections['profit_loss'] = self.extract_profit_loss(text)
        sections['balance_sheet'] = self.extract_balance_sheet(text)
        sections['notes'] = self.extract_notes(text)
        sections['turnover_note'] = self.extract_turnover_breakdown(text)
        
        logger.info("Sections extracted",
                   profit_loss_length=len(sections.get('profit_loss', '')),
                   balance_sheet_length=len(sections.get('balance_sheet', '')),
                   notes_length=len(sections.get('notes', '')))
        
        return sections
    
    def extract_profit_loss(self, text: str) -> str:
        """
        Extract the Profit and Loss Account section
        """
        return self._extract_section(
            text,
            self.section_config['profit_loss']['start_patterns'],
            self.section_config['profit_loss']['end_patterns']
        )
    
    def extract_balance_sheet(self, text: str) -> str:
        """
        Extract the Balance Sheet section
        """
        return self._extract_section(
            text,
            self.section_config['balance_sheet']['start_patterns'],
            ["Statement of changes in equity", "Statement of cash flows", "Notes to the"]
        )
    
    def extract_notes(self, text: str) -> str:
        """
        Extract the Notes to Financial Statements section
        """
        return self._extract_section(
            text,
            self.section_config['notes']['start_patterns'],
            ["This document was delivered", "END OF DOCUMENT", "Company registration number"]
        )
    
    def extract_turnover_breakdown(self, text: str) -> str:
        """
        Extract Note 3 (Turnover breakdown) specifically
        """
        notes_text = self.extract_notes(text)
        
        # Look for Note 3 or Turnover section
        patterns = [
            r"3[\s\n]+Turnover.*?(?=\n\s*\d+\s+\w+|\n\s*4\s+|\Z)",
            r"Turnover analysed by class.*?(?=\n\s*\d+\s+\w+|\n\s*4\s+|\Z)",
            r"Turnover and other revenue.*?(?=\n\s*\d+\s+\w+|\n\s*4\s+|\Z)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, notes_text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""
    
    def _extract_section(self, text: str, start_patterns: List[str], end_patterns: List[str]) -> str:
        """
        Generic section extraction between start and end patterns
        """
        # Find start position
        start_pos = None
        for pattern in start_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_pos = match.start()
                break
        
        if start_pos is None:
            return ""
        
        # Find end position
        end_pos = len(text)
        for pattern in end_patterns:
            match = re.search(pattern, text[start_pos:], re.IGNORECASE)
            if match:
                end_pos = start_pos + match.start()
                break
        
        return text[start_pos:end_pos]
    
    def find_specific_note(self, text: str, note_number: int) -> str:
        """
        Extract a specific numbered note
        """
        pattern = rf"{note_number}[\s\n]+\w+.*?(?=\n\s*{note_number+1}\s+\w+|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(0) if match else ""