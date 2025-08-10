import re
from typing import Dict, Any, Optional, List, Union
import structlog

from app.config.document_types.uk_football_financials import UK_FOOTBALL_FINANCIAL_CONFIG

logger = structlog.get_logger()

class UKFinancialFieldExtractor:
    """
    Extracts financial fields with UK accounting format understanding
    """
    
    def __init__(self):
        self.config = UK_FOOTBALL_FINANCIAL_CONFIG
        self.field_mappings = self.config["field_mappings"]
        self.number_formats = self.config["number_formats"]
        
    def extract_all_fields(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract all financial fields from document sections
        """
        result = {}
        
        # Extract from each section
        if sections.get('profit_loss'):
            result.update(self.extract_pl_fields(sections['profit_loss']))
            
        if sections.get('balance_sheet'):
            result.update(self.extract_bs_fields(sections['balance_sheet']))
            
        if sections.get('notes') or sections.get('turnover_note'):
            result.update(self.extract_revenue_breakdown(
                sections.get('turnover_note') or sections.get('notes', '')
            ))
        
        # Apply post-processing rules
        result = self.apply_post_processing(result)
        
        # Validate the results
        validation = self.validate_financials(result)
        if not validation['is_valid']:
            logger.warning("Validation issues found",
                          issues=validation['issues'])
        
        return result
    
    def extract_pl_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract Profit & Loss fields with UK format handling
        """
        fields = {}
        
        # Key P&L fields to extract
        pl_patterns = {
            'turnover': [
                r'Turnover\s+(?:3\s+)?[\s\n]*([\d,]+)',
                r'Turnover\s+£?\s*([\d,]+)',
                r'Revenue\s+£?\s*([\d,]+)'
            ],
            'cost_of_sales': [
                r'Cost of sales\s+\(([\d,]+)\)',
                r'Cost of sales\s+£?\s*\(([\d,]+)\)'
            ],
            'gross_profit': [
                r'Gross profit(?:/\(loss\))?\s+([\d,]+)',
                r'Gross profit\s+£?\s*([\d,]+)'
            ],
            'administrative_expenses': [
                r'Administrative expenses\s+\(([\d,]+)\)',
                r'Administrative expenses\s+£?\s*\(([\d,]+)\)'
            ],
            'operating_profit': [
                r'Operating (?:profit|loss)\s+\(([\d,]+)\)',
                r'Operating (?:profit|loss)\s+([\d,]+)',
                r'Operating profit/\(loss\)\s+\(([\d,]+)\)'
            ],
            'profit_loss_before_tax': [
                r'(?:Profit|Loss) before tax(?:ation)?\s+\(([\d,]+)\)',
                r'(?:Profit|Loss) before tax(?:ation)?\s+([\d,]+)',
                r'Loss for the financial year\s+\(([\d,]+)\)'
            ]
        }
        
        for field_name, patterns in pl_patterns.items():
            value = self._extract_with_patterns(text, patterns)
            if value is not None:
                # Check if it's negative (in parentheses)
                if self._is_negative_in_text(text, value):
                    value = -abs(value)
                fields[field_name] = value
        
        return fields
    
    def extract_bs_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract Balance Sheet fields with UK format handling
        """
        fields = {}
        
        bs_patterns = {
            'total_assets': [
                r'Total assets\s+£?\s*([\d,]+)',
                r'Fixed assets[\s\S]*?Current assets[\s\S]*?(?:Total|£)\s+([\d,]+)'
            ],
            'cash_at_bank': [
                r'Cash at bank and in hand\s+£?\s*([\d,]+)',
                r'Cash and cash equivalents\s+£?\s*([\d,]+)',
                r'Cash\s+£?\s*([\d,]+)'
            ],
            'creditors_due_within_one_year': [
                r'Creditors:\s*amounts falling due within one year\s+\(([\d,]+)\)',
                r'Creditors due within one year\s+\(([\d,]+)\)',
                r'Current liabilities\s+\(([\d,]+)\)'
            ],
            'creditors_due_after_one_year': [
                r'Creditors:\s*amounts falling due after (?:more than )?one year\s+\(([\d,]+)\)',
                r'(?:Creditors|amounts) falling due after (?:more than )?one year\s+\(([\d,]+)\)',
                r'Non-current liabilities\s+\(([\d,]+)\)'
            ],
            'net_assets': [
                r'Net assets\s+£?\s*([\d,]+)',
                r'Net liabilities\s+\(([\d,]+)\)',
                r'Net assets/\(liabilities\)\s+\(([\d,]+)\)',
                r'Total equity\s+\(([\d,]+)\)'
            ],
            'net_current_liabilities': [
                r'Net current (?:assets|liabilities)\s+\(([\d,]+)\)',
                r'Net current (?:assets|liabilities)\s+([\d,]+)'
            ]
        }
        
        for field_name, patterns in bs_patterns.items():
            value = self._extract_with_patterns(text, patterns)
            if value is not None:
                # Special handling for creditors and liabilities
                if 'creditors' in field_name or 'liabilities' in field_name:
                    if self._is_negative_in_text(text, value):
                        value = -abs(value)
                # Net liabilities is negative net assets
                elif field_name == 'net_assets' and 'Net liabilities' in text:
                    value = -abs(value)
                    
                fields[field_name] = value
        
        return fields
    
    def extract_revenue_breakdown(self, text: str) -> Dict[str, Any]:
        """
        Extract revenue breakdown from notes
        """
        fields = {}
        
        revenue_patterns = {
            'matchday_revenue': [
                r'Matchday(?:\s+(?:Admissions|income))?\s+£?\s*([\d,]+)',
                r'Gate receipts\s+£?\s*([\d,]+)',
                r'Matchday\s+[\d,]+\s+£?\s*([\d,]+)'  # For year comparisons
            ],
            'broadcasting_revenue': [
                r'Broadcasting(?:\s+revenue)?\s+£?\s*([\d,]+)',
                r'TV revenue\s+£?\s*([\d,]+)',
                r'Media revenue\s+£?\s*([\d,]+)'
            ],
            'commercial_revenue': [
                r'Commercial(?:\s+revenue)?\s+£?\s*([\d,]+)',
                r'Sponsorship and Advertising\s+£?\s*([\d,]+)',
                r'Sponsorship\s+£?\s*([\d,]+)'
            ]
        }
        
        for field_name, patterns in revenue_patterns.items():
            value = self._extract_with_patterns(text, patterns)
            if value is not None:
                fields[field_name] = value
        
        return fields
    
    def _extract_with_patterns(self, text: str, patterns: List[str]) -> Optional[float]:
        """
        Try multiple patterns to extract a numeric value
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                # Extract the number
                number_str = match.group(1)
                # Remove commas and convert to float
                number = float(number_str.replace(',', ''))
                
                # Check for scale indicators (thousands, millions)
                if "'000" in text[:match.start() + 50] or "£'000" in text[:match.start() + 50]:
                    number *= 1000
                elif "£m" in text[:match.start() + 50] or "millions" in text[:match.start() + 50]:
                    number *= 1000000
                    
                return number
        
        return None
    
    def _is_negative_in_text(self, text: str, value: float) -> bool:
        """
        Check if a value appears in parentheses in the text (indicating negative)
        """
        # Look for the value in parentheses
        value_str = f"{int(value):,}"
        patterns = [
            rf'\({value_str}\)',
            rf'\(£{value_str}\)',
            rf'\(£?\s*{value_str}\)'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def apply_post_processing(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply post-processing rules from configuration
        """
        # Fix common issues
        
        # 1. Ensure creditors are negative
        for field in ['creditors_due_within_one_year', 'creditors_due_after_one_year']:
            if field in fields and fields[field] > 0:
                fields[field] = -fields[field]
        
        # 2. Calculate missing total_liabilities if we have the components
        if 'total_liabilities' not in fields:
            if 'creditors_due_within_one_year' in fields and 'creditors_due_after_one_year' in fields:
                fields['total_liabilities'] = (
                    fields.get('creditors_due_within_one_year', 0) + 
                    fields.get('creditors_due_after_one_year', 0)
                )
        
        # 3. Validate/fix net assets calculation
        if 'total_assets' in fields and 'total_liabilities' in fields:
            calculated_net_assets = fields['total_assets'] + fields['total_liabilities']  # liabilities are negative
            
            if 'net_assets' in fields:
                # Check if calculation matches
                if abs(calculated_net_assets - fields['net_assets']) > 1000:
                    logger.warning("Net assets calculation mismatch",
                                 reported=fields['net_assets'],
                                 calculated=calculated_net_assets)
            else:
                fields['net_assets'] = calculated_net_assets
        
        return fields
    
    def validate_financials(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the extracted financial data
        """
        issues = []
        
        # Check balance sheet equation
        if all(k in fields for k in ['total_assets', 'total_liabilities', 'net_assets']):
            calculated = fields['total_assets'] + fields['total_liabilities']
            if abs(calculated - fields['net_assets']) > 1000:
                issues.append(f"Balance sheet doesn't balance: {calculated} != {fields['net_assets']}")
        
        # Check revenue breakdown
        if 'turnover' in fields:
            revenue_sum = sum([
                fields.get('matchday_revenue', 0),
                fields.get('broadcasting_revenue', 0),
                fields.get('commercial_revenue', 0)
            ])
            
            if revenue_sum > 0:
                diff_pct = abs(revenue_sum - fields['turnover']) / fields['turnover']
                if diff_pct > 0.1:  # More than 10% difference
                    issues.append(f"Revenue breakdown doesn't match turnover: {revenue_sum} vs {fields['turnover']}")
        
        # Check for reasonable ranges
        if 'turnover' in fields and fields['turnover'] < 100000:
            issues.append("Turnover seems too low - check for scale issues (thousands?)")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }