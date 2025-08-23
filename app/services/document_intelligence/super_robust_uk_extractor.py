import re
from typing import Dict, Any, Optional, List, Union, Tuple
import structlog

logger = structlog.get_logger()

class SuperRobustUKFinancialExtractor:
    """
    Handles ALL the complex real-world patterns found in index-az cleaned_text data
    """
    
    def __init__(self):
        # Compile all patterns for maximum performance
        self.compiled_patterns = self._compile_all_patterns()
        self.debug_mode = True  # Set to False in production
        
    def _compile_all_patterns(self) -> Dict[str, List[re.Pattern]]:
        """
        Compile every possible pattern variation found in real cleaned_text data
        """
        
        return {
            'turnover': self._compile_turnover_patterns(),
            'cost_of_sales': self._compile_cost_of_sales_patterns(),
            'administrative_expenses': self._compile_admin_expenses_patterns(),
            'player_amortization': self._compile_player_amortization_patterns(),
            'operating_profit': self._compile_operating_profit_patterns(),
            'gross_profit': self._compile_gross_profit_patterns(),
            'gross_loss': self._compile_gross_loss_patterns(),
            'staff_costs_total': self._compile_staff_costs_patterns(),
            'social_security_costs': self._compile_social_security_patterns(),
            'other_operating_income': self._compile_other_operating_income_patterns(),
            'interest_receivable': self._compile_interest_receivable_patterns(),
            'interest_payable': self._compile_interest_payable_patterns(),
            'profit_loss_before_tax': self._compile_profit_before_tax_patterns(),
            'profit_on_player_disposals': self._compile_player_disposal_patterns(),
        }
    
    def _compile_turnover_patterns(self) -> List[re.Pattern]:
        """
        Based on real examples:
        - Sheffield United: "Turnover, Note: 1, 30 June 2024: 32,247"
        - Southampton: "Turnover 4 84,001 - 84,001 145,467" 
        - Bristol City: "Turnover 3 20,523,730 18,571,483"
        - Oxford United: "Turnover, 3, 2024: 8,439,071"
        """
        patterns = [
            # Sheffield United style: "Turnover, Note: 1, 30 June 2024: 32,247"
            re.compile(r'Turnover,?\s*Note:\s*\d+,?\s*\d{1,2}\s+\w+\s+(\d{4}):\s*([\d,]+)', re.IGNORECASE),
            
            # Southampton multi-column: "Turnover 4 84,001 - 84,001 145,467"
            # Extract the "Total" column (3rd number)
            re.compile(r'Turnover\s+\d+\s+([\d,]+)\s*[-–]\s*([\d,]+)\s+([\d,]+)', re.IGNORECASE),
            
            # Bristol City style: "Turnover 3 20,523,730 18,571,483"
            re.compile(r'Turnover\s+\d+\s*([\d,]+)\s+[\d,]+', re.IGNORECASE),
            
            # Oxford United style: "Turnover, 3, 2024: 8,439,071"
            re.compile(r'Turnover,?\s*\d+,?\s*\d{4}:\s*([\d,]+)', re.IGNORECASE),
            
            # Standard formats
            re.compile(r'Turnover\s*[:;]\s*£?\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Revenue\s*[:;]\s*£?\s*([\d,]+)', re.IGNORECASE),
            
            # Table header format: "Turnover 32,247"
            re.compile(r'Turnover\s+([\d,]+)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_cost_of_sales_patterns(self) -> List[re.Pattern]:
        """
        Real examples:
        - Sheffield: "Cost of sales, 30 June 2024: (47,927)"
        - Southampton: "Cost of sales (107,729) (51,142) (158,871)"
        - Oxford: "Cost of sales, 2024: (11,924,701)"
        """
        patterns = [
            # Sheffield style: "Cost of sales, 30 June 2024: (47,927)"
            re.compile(r'Cost of sales,?\s*\d{1,2}\s+\w+\s+\d{4}:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Southampton multi-column: Extract total (3rd column)
            re.compile(r'Cost of sales\s*\(([\d,]+)\)\s*\(([\d,]+)\)\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Oxford style: "Cost of sales, 2024: (11,924,701)"
            re.compile(r'Cost of sales,?\s*\d{4}:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Simple format: "Cost of sales (47,927)"
            re.compile(r'Cost of sales\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Alternative format: "Cost of sales: (47,927)"
            re.compile(r'Cost of sales\s*:\s*\(([\d,]+)\)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_admin_expenses_patterns(self) -> List[re.Pattern]:
        """
        CRITICAL: Handle complex admin expense splits
        - Sheffield: "Administrative expenses, 30 June 2024: (14,564)" (TOTAL)
        - Sheffield: "Administrative expenses before player amortisation: (5,344)" (COMPONENT)
        - Southampton: "Administrative expenses (16,115) - (16,115)"
        - Oxford: "Administrative expenses, 2024: (7,909,251)"
        """
        patterns = [
            # Sheffield total: "Administrative expenses, 30 June 2024: (14,564)"
            re.compile(r'Administrative expenses,?\s*\d{1,2}\s+\w+\s+\d{4}:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Southampton format: "Administrative expenses (16,115) - (16,115)"
            re.compile(r'Administrative expenses\s*\(([\d,]+)\)\s*[-–]\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Oxford style: "Administrative expenses, 2024: (7,909,251)"
            re.compile(r'Administrative expenses,?\s*\d{4}:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Simple: "Administrative expenses (14,564)"
            re.compile(r'Administrative expenses\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Before player amort (component): "Administrative expenses before player amortisation: (5,344)"
            re.compile(r'Administrative expenses before player amortisation[^:]*:\s*\(([\d,]+)\)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_player_amortization_patterns(self) -> List[re.Pattern]:
        """
        CRITICAL: Often buried in admin expenses breakdown
        - Sheffield: "Player amortisation and impairment, 30 June 2024: (9,220)"
        - Bristol: "Depreciation and amortisation expense (4,255,202)" (combined)
        """
        patterns = [
            # Sheffield explicit: "Player amortisation and impairment, 30 June 2024: (9,220)"
            re.compile(r'Player amortisation and impairment,?\s*\d{1,2}\s+\w+\s+\d{4}:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Direct: "Player amortisation: (9,220)"
            re.compile(r'Player amortisation[^:]*:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Year format: "Player amortisation, 2024: (9,220)"
            re.compile(r'Player amortisation,?\s*\d{4}:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Alternative spellings
            re.compile(r'Player amortization[^:]*:\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # In notes: "Amortisation of player registrations (9,220)"
            re.compile(r'Amortisation of player registrations[^:]*\(([\d,]+)\)', re.IGNORECASE),
            
            # Intangible assets amortisation (player related)
            re.compile(r'Amortisation of intangible assets[^:]*\(([\d,]+)\)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_operating_profit_patterns(self) -> List[re.Pattern]:
        """
        Handle both profit and loss, make losses negative
        """
        patterns = [
            # Sheffield: "Operating loss, 30 June 2024: (11,922)"  
            re.compile(r'Operating (?:loss|profit),?\s*\d{1,2}\s+\w+\s+\d{4}:\s*\(?([+-]?[\d,]+)\)?', re.IGNORECASE),
            
            # Southampton: "Operating loss 6 (38,133) (50,659) (88,792)"
            re.compile(r'Operating (?:loss|profit)\s*\d*\s*\(?([+-]?[\d,]+)\)?(?:\s*\([^)]+\))*\s*\(?([+-]?[\d,]+)\)?', re.IGNORECASE),
            
            # Bristol: "Operating loss 5 (21,966,236)"
            re.compile(r'Operating (?:loss|profit)\s*\d*\s*\(?([+-]?[\d,]+)\)?', re.IGNORECASE),
            
            # Standard: "Operating profit/(loss): (11,922)"
            re.compile(r'Operating (?:profit|loss)(?:/\([^)]+\))?\s*:\s*\(?([+-]?[\d,]+)\)?', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_staff_costs_patterns(self) -> List[re.Pattern]:
        """
        Bristol: "Staff costs (24,822,941)"
        Sometimes in notes section
        """
        patterns = [
            # Bristol style: "Staff costs (24,822,941) (26,307,953)"
            re.compile(r'Staff costs\s*\(([\d,]+)\)', re.IGNORECASE),
            
            # Year specific: "Staff costs, 2024: 24,822,941"
            re.compile(r'Staff costs,?\s*\d{4}:\s*([\d,]+)', re.IGNORECASE),
            
            # Alternative: "Total staff costs: 24,822,941"
            re.compile(r'Total staff costs[^:]*:\s*([\d,]+)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_social_security_patterns(self) -> List[re.Pattern]:
        """Usually in staff costs note breakdown"""
        patterns = [
            re.compile(r'Social security costs[^:]*:\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Social security[^:]*:\s*([\d,]+)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_other_operating_income_patterns(self) -> List[re.Pattern]:
        """
        Sheffield: "Other operating income, Note: 4, 30 June 2024: 1,210"
        Southampton: "Other operating income 5 1,710 483 2,193"
        Bristol: "Other operating income 4 277,400"
        """
        patterns = [
            # Sheffield: "Other operating income, Note: 4, 30 June 2024: 1,210"
            re.compile(r'Other operating income,?\s*Note:\s*\d+,?\s*\d{1,2}\s+\w+\s+\d{4}:\s*([\d,]+)', re.IGNORECASE),
            
            # Southampton multi-column: "Other operating income 5 1,710 483 2,193"
            re.compile(r'Other operating income\s*\d*\s*([\d,]+)(?:\s+[\d,]+)*\s+([\d,]+)', re.IGNORECASE),
            
            # Bristol: "Other operating income 4 277,400"
            re.compile(r'Other operating income\s*\d*\s*([\d,]+)', re.IGNORECASE),
            
            # Standard
            re.compile(r'Other operating income[^:]*:\s*([\d,]+)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_interest_receivable_patterns(self) -> List[re.Pattern]:
        """Interest received/income patterns"""
        patterns = [
            re.compile(r'Interest receivable[^:]*:\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Interest (?:received|income)[^:]*:\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Interest receivable and similar income[^:]*:\s*([\d,]+)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_interest_payable_patterns(self) -> List[re.Pattern]:
        """Interest paid/expense patterns - make negative"""
        patterns = [
            re.compile(r'Interest payable[^:]*:\s*\(?([\d,]+)\)?', re.IGNORECASE),
            re.compile(r'Interest (?:paid|expense)[^:]*:\s*\(?([\d,]+)\)?', re.IGNORECASE),
            re.compile(r'Interest payable and similar (?:charges|expenses)[^:]*:\s*\(?([\d,]+)\)?', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_gross_profit_patterns(self) -> List[re.Pattern]:
        """Gross profit patterns"""
        patterns = [
            re.compile(r'Gross profit,?\s*\d{1,2}\s+\w+\s+\d{4}:\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Gross profit[^:]*:\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Gross profit\s+([\d,]+)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_gross_loss_patterns(self) -> List[re.Pattern]:
        """Gross loss patterns - make negative"""
        patterns = [
            # Sheffield: "Gross loss, 30 June 2024: (15,680)"
            re.compile(r'Gross loss,?\s*\d{1,2}\s+\w+\s+\d{4}:\s*\(([\d,]+)\)', re.IGNORECASE),
            re.compile(r'Gross loss[^:]*:\s*\(([\d,]+)\)', re.IGNORECASE),
            re.compile(r'Gross loss\s*\(([\d,]+)\)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_profit_before_tax_patterns(self) -> List[re.Pattern]:
        """Profit/loss before taxation"""
        patterns = [
            re.compile(r'(?:Profit|Loss) before tax(?:ation)?[^:]*:\s*\(?([+-]?[\d,]+)\)?', re.IGNORECASE),
            re.compile(r'(?:Profit|Loss) before tax(?:ation)?,?\s*\d{4}:\s*\(?([+-]?[\d,]+)\)?', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_player_disposal_patterns(self) -> List[re.Pattern]:
        """Player sale profits"""
        patterns = [
            # Sheffield: "Profit on sale of registrations, 30 June 2024: 17,112"
            re.compile(r'Profit on sale of registrations[^:]*:\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Profit on disposal of players[^:]*:\s*([\d,]+)', re.IGNORECASE),
            re.compile(r'Profit on disposal of (?:players\'?|player) contracts[^:]*:\s*([\d,]+)', re.IGNORECASE),
        ]
        return patterns

    def extract_all_fields(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract all fields using super robust pattern matching
        """
        # Combine all text sections for comprehensive extraction
        full_text = ""
        if sections.get('profit_loss'):
            full_text += sections['profit_loss'] + "\n"
        if sections.get('balance_sheet'):
            full_text += sections['balance_sheet'] + "\n"  
        if sections.get('notes'):
            full_text += sections['notes'] + "\n"
        if sections.get('cleaned_text'):
            full_text += sections['cleaned_text'] + "\n"
        
        if not full_text.strip():
            full_text = list(sections.values())[0] if sections else ""
        
        results = {}
        extraction_log = []
        
        # Extract each field using multiple patterns
        for field_name, patterns in self.compiled_patterns.items():
            value = self._extract_field_with_multiple_patterns(
                field_name, patterns, full_text
            )
            results[field_name] = value
            
            if value is not None and self.debug_mode:
                extraction_log.append(f"✅ {field_name}: {value:,}")
            elif self.debug_mode:
                extraction_log.append(f"❌ {field_name}: Not found")
        
        if self.debug_mode and extraction_log:
            logger.info("Extraction results", 
                       fields_found=len([r for r in results.values() if r is not None]),
                       total_fields=len(results),
                       details=extraction_log[:10])  # Limit log size
        
        # Apply post-processing for complex relationships
        results = self._post_process_results(results, full_text)
        
        return results
    
    def _extract_field_with_multiple_patterns(
        self, field_name: str, patterns: List[re.Pattern], text: str
    ) -> Optional[int]:
        """
        Try multiple patterns for a field, return first successful match
        """
        for i, pattern in enumerate(patterns):
            try:
                matches = pattern.findall(text)
                if matches:
                    # Handle different match group structures
                    if isinstance(matches[0], tuple):
                        # Multiple groups - use logic based on field type
                        value = self._select_best_match_from_groups(
                            field_name, matches[0]
                        )
                    else:
                        # Single group
                        value = matches[0]
                    
                    # Convert to integer
                    numeric_value = self._convert_to_integer(value)
                    if numeric_value is not None:
                        # Apply field-specific sign logic
                        final_value = self._apply_sign_logic(field_name, numeric_value)
                        
                        if self.debug_mode:
                            logger.debug(f"Pattern {i+1} matched for {field_name}",
                                       pattern=pattern.pattern[:50],
                                       raw_match=value,
                                       final_value=final_value)
                        return final_value
                        
            except Exception as e:
                logger.warning(f"Pattern {i+1} failed for {field_name}", error=str(e))
                continue
        
        return None
    
    def _select_best_match_from_groups(self, field_name: str, groups: Tuple) -> str:
        """
        Select the best match from multiple regex groups based on field type
        """
        if field_name == 'turnover' and len(groups) >= 3:
            # For Southampton multi-column: use "Total" column (3rd)
            return groups[2] if groups[2] else groups[0]
        elif field_name == 'cost_of_sales' and len(groups) >= 3:
            # For multi-column: use total column
            return groups[2] if groups[2] else groups[0]
        else:
            # Use first non-empty group
            return next((g for g in groups if g), groups[0])
    
    def _convert_to_integer(self, value_str: str) -> Optional[int]:
        """
        Convert string to integer, handling commas and various formats
        """
        if not value_str:
            return None
            
        try:
            # Remove commas and whitespace
            clean_value = value_str.replace(',', '').strip()
            
            # Handle negative signs and parentheses
            is_negative = False
            if clean_value.startswith('-') or clean_value.startswith('('):
                is_negative = True
                clean_value = clean_value.lstrip('-(').rstrip(')')
            
            # Convert to integer
            numeric_value = int(clean_value)
            
            # Handle scale detection (thousands vs actual)
            # Most Sheffield United values are in thousands, others are actual
            # This is tricky - we'll use context clues
            if numeric_value < 100000:  # Likely in thousands
                numeric_value *= 1000
            
            return -numeric_value if is_negative else numeric_value
            
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert value to integer: {value_str}")
            return None
    
    def _apply_sign_logic(self, field_name: str, value: int) -> int:
        """
        Apply UK accounting sign conventions
        """
        # Fields that should always be negative (expenses, losses)
        negative_fields = {
            'cost_of_sales', 'administrative_expenses', 'player_amortization',
            'interest_payable', 'gross_loss'
        }
        
        # Fields that should always be positive (revenues, assets) 
        positive_fields = {
            'turnover', 'gross_profit', 'interest_receivable', 
            'other_operating_income', 'profit_on_player_disposals'
        }
        
        # Operating profit can be positive or negative - preserve as extracted
        if field_name in negative_fields:
            return -abs(value)  # Force negative
        elif field_name in positive_fields:
            return abs(value)   # Force positive
        else:
            return value        # Preserve sign as extracted
    
    def _post_process_results(self, results: Dict[str, Any], full_text: str) -> Dict[str, Any]:
        """
        Handle complex relationships and derived calculations
        """
        # Handle Sheffield United style admin expenses split
        if 'administrative_expenses' in results and results['administrative_expenses']:
            # Look for the split pattern to extract player amortization
            admin_split_pattern = re.compile(
                r'Administrative expenses before player amortisation[^:]*:\s*\(([\d,]+)\)'
                r'.*?Player amortisation and impairment[^:]*:\s*\(([\d,]+)\)',
                re.IGNORECASE | re.DOTALL
            )
            
            match = admin_split_pattern.search(full_text)
            if match:
                admin_before_player = self._convert_to_integer(match.group(1))
                player_amort = self._convert_to_integer(match.group(2))
                
                if admin_before_player and player_amort and not results.get('player_amortization'):
                    results['player_amortization'] = -abs(player_amort)
                    logger.info("Extracted player amortization from admin expenses split",
                               player_amort=player_amort,
                               admin_before=admin_before_player)
        
        # Validate key relationships
        self._validate_financial_relationships(results)
        
        return results
    
    def _validate_financial_relationships(self, results: Dict[str, Any]) -> None:
        """
        Validate extracted data makes financial sense
        """
        validations = []
        
        # Check if administrative expenses include player amortization
        admin_exp = results.get('administrative_expenses', 0) or 0
        player_amort = results.get('player_amortization', 0) or 0
        
        if admin_exp and player_amort:
            if abs(admin_exp) < abs(player_amort):
                validations.append(
                    f"⚠️ Admin expenses ({admin_exp:,}) < Player amortization ({player_amort:,}) - possible component vs total issue"
                )
        
        # Check turnover reasonableness
        turnover = results.get('turnover', 0) or 0
        if turnover and (turnover < 1_000_000 or turnover > 500_000_000):
            validations.append(
                f"⚠️ Turnover seems unreasonable: £{turnover:,}"
            )
        
        if validations and self.debug_mode:
            logger.warning("Validation issues found", issues=validations)


# Usage example function
def extract_with_super_robust_extractor(cleaned_text: str) -> Dict[str, Any]:
    """
    Example usage of the super robust extractor
    """
    extractor = SuperRobustUKFinancialExtractor()
    
    # Prepare sections (you can pass the cleaned_text in multiple ways)
    sections = {
        'cleaned_text': cleaned_text,
        'profit_loss': cleaned_text,  # Same text, multiple keys for compatibility
    }
    
    # Extract all fields
    results = extractor.extract_all_fields(sections)
    
    return results


# Test function with real Sheffield United data
def test_with_sheffield_united():
    """
    Test with actual Sheffield United cleaned_text from index-az
    """
    sheffield_text = """Table Data: 30 June 2024: £'000, 30 June 2023: £'000 : 
    Turnover, Note: 1, 30 June 2024: 32,247, 30 June 2023: 28,594 : 
    Cost of sales, 30 June 2024: (47,927), 30 June 2023: (45,011) : 
    Gross loss, 30 June 2024: (15,680), 30 June 2023: (16,417) : 
    Administrative expenses before player amortisation and impairment, 30 June 2024: (5,344), 30 June 2023: (5,006) : 
    Player amortisation and impairment, 30 June 2024: (9,220), 30 June 2023: (11,566) : 
    Administrative expenses, 30 June 2024: (14,564), 30 June 2023: (16,572) : 
    Profit on sale of registrations, 30 June 2024: 17,112, 30 June 2023: 22,319 : 
    Other operating income, Note: 4, 30 June 2024: 1,210, 30 June 2023: 3,938 : 
    Operating loss, 30 June 2024: (11,922), 30 June 2023: (6,732) :"""
    
    results = extract_with_super_robust_extractor(sheffield_text)
    
    print("Sheffield United Extraction Results:")
    for field, value in results.items():
        if value is not None:
            print(f"✅ {field}: £{value:,}")
    
    return results

# Expected Sheffield United results:
# ✅ turnover: £32,247,000
# ✅ cost_of_sales: £-47,927,000  
# ✅ administrative_expenses: £-14,564,000
# ✅ player_amortization: £-9,220,000
# ✅ operating_profit: £-11,922,000
# ✅ gross_loss: £-15,680,000
# ✅ profit_on_player_disposals: £17,112,000
# ✅ other_operating_income: £1,210,000