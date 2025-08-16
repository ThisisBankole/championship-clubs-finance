from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from openai import AzureOpenAI
import json
import os
import logging
import re

logger = logging.getLogger(__name__)

# Azure OpenAI configuration
ENDPOINT = "https://club-fin-index.cognitiveservices.azure.com/"
DEPLOYMENT = "gpt-4.1"
API_VERSION = "2024-12-01-preview"
API_KEY = os.environ.get("AZURE_AI_FOUNDRY_API_KEY")

router = APIRouter()

# Define TextSection FIRST
class TextSection(BaseModel):
    id: str
    content: str
    locationMetadata: Optional[Dict[str, Any]] = None
    sections: Optional[List[Any]] = None

# Then define InputData that uses TextSection
class InputData(BaseModel):
    text: Optional[str] = None
    text_sections: Optional[List[TextSection]] = None

class RecordValue(BaseModel):
    recordId: str
    data: InputData

class SkillRequest(BaseModel):
    values: List[RecordValue]

class FinancialData(BaseModel):
    is_abridged: Optional[bool] = None
    revenue: Optional[float] = None
    turnover: Optional[float] = None
    operating_expenses: Optional[float] = None
    net_income: Optional[float] = None
    
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    
    net_assets: Optional[float] = None
    cash_at_bank: Optional[float] = None
    cash_and_cash_equivalents: Optional[float] = None
    creditors_due_within_one_year: Optional[float] = None
    creditors_due_after_one_year: Optional[float] = None
    operating_profit: Optional[float] = None
    profit_loss_before_tax: Optional[float] = None
    broadcasting_revenue: Optional[float] = None
    commercial_revenue: Optional[float] = None
    matchday_revenue: Optional[float] = None
    player_trading_income: Optional[float] = None
    player_wages: Optional[float] = None
    player_amortization: Optional[float] = None
    other_staff_costs: Optional[float] = None
    stadium_costs: Optional[float] = None
    administrative_expenses: Optional[float] = None
    agent_fees: Optional[float] = None
   
    cost_of_sales: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_loss: Optional[float] = None


    interest_receivable: Optional[float] = None
    interest_payable: Optional[float] = None
    other_operating_income: Optional[float] = None

   
    staff_costs_total: Optional[float] = None
    social_security_costs: Optional[float] = None
    pension_costs: Optional[float] = None
    depreciation_charges: Optional[float] = None
    operating_lease_charges: Optional[float] = None

  
    profit_on_player_disposals: Optional[float] = None
    loss_on_player_disposals: Optional[float] = None


    intangible_assets: Optional[float] = None
    tangible_assets: Optional[float] = None
    current_assets: Optional[float] = None
    stocks: Optional[float] = None
    debtors: Optional[float] = None

   
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None


    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    debt_to_equity_ratio: Optional[float] = None
    
    

   
    document_type: Optional[str] = None
    profit_loss_filed: Optional[bool] = None

class RecordError(BaseModel):
    message: str

class RecordResult(BaseModel):
    recordId: str
    data: FinancialData
    errors: Optional[List[RecordError]] = None

class SkillResponse(BaseModel):
    values: List[RecordResult]


def remove_ocr_artifacts(text: str) -> str:
    """
    Remove OCR scanning artifacts and metadata - THIS WAS MISSING!
    """
    
    # Remove coordinate/metadata artifacts
    text = re.sub(r'\{[^}]*\}', '', text)  # Remove JSON objects
    text = re.sub(r'boundingPolygons.*?\]\]', '', text)  # Remove coordinates
    text = re.sub(r'pageNumber.*?\d+', '', text)  # Remove page references
    text = re.sub(r'ordinalPosition.*?\d+', '', text)  # Remove position data
    text = re.sub(r'locationMetadata.*?sections', '', text)  # Remove location data
    
    # Remove common OCR scanning artifacts
    text = re.sub(r'FRIDAY\*[A-Z0-9\*\[\]]+', '', text)  # Remove scan codes
    text = re.sub(r'COMPANIES HOUSE#\d+', '', text)  # Remove filing references
    text = re.sub(r'A\d+\s+\d{2}/\d{2}/\d{4}', '', text)  # Remove date stamps
    
    # Remove duplicate document headers
    text = re.sub(r'(WEST BROMWICH ALBION FOOTBALL CLUB LIMITED\s*){2,}', 
                  'WEST BROMWICH ALBION FOOTBALL CLUB LIMITED ', text)
    
    return text

def clean_company_info(text: str) -> str:
    """
    Clean up director names and company information - THIS WAS MISSING!
    """
    
    # Fix concatenated director names: "DirectorsM MilesS Patel" -> "Directors: M Miles, S Patel"
    text = re.sub(r'Directors([A-Z][a-z]+(?:[A-Z][a-z]+)*)', 
                  lambda m: f"Directors: {' '.join(re.findall(r'[A-Z][a-z]+', m.group(1)))}", text)
    
    # Fix company number formatting
    text = re.sub(r'Company number(\d+)', r'Company number: \1', text)
    
    # Fix address formatting: remove excessive concatenation
    text = re.sub(r'United Kingdom([A-Z0-9 ]+)', r'United Kingdom \1', text)
    
    # Clean up audit information
    text = re.sub(r'Auditor([A-Z])', r'Auditor: \1', text)
    
    return text

def clean_ocr_text(text: str) -> str:
    """
    Clean OCR text to fix common formatting issues before GPT extraction
    """
    
    # Remove excessive whitespace and newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'\s+', ' ', text)
    
    # ENHANCED: Remove OCR artifacts and metadata first
    text = remove_ocr_artifacts(text)
    
    # Fix common OCR issues
    text = fix_number_formatting(text)
    text = fix_financial_labels(text)
    text = separate_concatenated_items(text)
    
    # ENHANCED: Clean up company info
    text = clean_company_info(text)
    
    return text.strip()

def fix_number_formatting(text: str) -> str:
    """
    Fix common number formatting issues in OCR text
    """
    
    # Fix concatenated parentheses: "123,456( 789,012)" -> "123,456 (789,012)"
    text = re.sub(r'(\d)(\()', r'\1 \2', text)
    
    # Fix missing spaces before parentheses in financial data
    text = re.sub(r'(\d)\(', r'\1 (', text)
    
    # Fix concatenated numbers: "123,456789,012" -> "123,456 789,012"
    text = re.sub(r'(\d{1,3}(?:,\d{3})*[^\s,\d])(\d)', r'\1 \2', text)
    
    # Add space after currency symbols
    text = re.sub(r'£(\d)', r'£ \1', text)
    
    return text

def fix_financial_labels(text: str) -> str:
    """
    Fix concatenated financial labels with numbers
    """
    
    # Common financial terms that get stuck to numbers
    financial_terms = [
        'Cash at bank', 'Net assets', 'Total assets', 'Turnover', 'Revenue',
        'Creditors', 'Profit', 'Loss', 'Tax', 'Interest', 'Broadcasting',
        'Commercial', 'Matchday', 'Player', 'Wages', 'Transfer', 'Stadium',
        'Company number', 'Registration number'  # Added more terms
    ]
    
    for term in financial_terms:
        # Fix cases like "Cash at bank123,456" -> "Cash at bank: 123,456"
        pattern = f'({re.escape(term)})(\d)'
        text = re.sub(pattern, r'\1: \2', text, flags=re.IGNORECASE)
        
        # Fix cases like "123,456Cash at bank" -> "123,456 Cash at bank"  
        pattern = f'(\d)({re.escape(term)})'
        text = re.sub(pattern, r'\1 \2', text, flags=re.IGNORECASE)
    
    return text

def separate_concatenated_items(text: str) -> str:
    """
    Separate concatenated financial statement items
    """
    
    # Separate items that are commonly concatenated in OCR
    # Example: "PROFIT BEFORE TAXATION3,334,238Interest receivable108,574"
    
    # Add space before capital letters that follow numbers
    text = re.sub(r'(\d)([A-Z][a-z])', r'\1 \2', text)
    
    # Add space before common financial statement starts
    financial_starts = ['PROFIT', 'LOSS', 'REVENUE', 'TURNOVER', 'CASH', 'NET', 'TOTAL', 'TAX']
    for start in financial_starts:
        text = re.sub(f'(\d)({start})', r'\1 \2', text)
    
    # Fix concatenated page references
    text = re.sub(r'(\w)(Page\s*\d+)', r'\1 \2', text, flags=re.IGNORECASE)
    
    return text

def extract_financial_context(text: str) -> str:
    """
    Extract the most relevant financial sections from the full text
    """
    
    # Look for key financial statement sections
    financial_keywords = [
        'profit and loss', 'balance sheet', 'cash flow', 'income statement',
        'revenue', 'turnover', 'broadcasting', 'commercial', 'matchday',
        'player wages', 'staff costs', 'amortisation', 'transfer',
        'cash at bank', 'net assets', 'creditors', 'liabilities'  # Added more keywords
    ]
    
    # Split text into chunks and rank by financial relevance
    chunks = text.split('\n')
    relevant_chunks = []
    
    for chunk in chunks:
        if len(chunk.strip()) < 10:  # Skip very short lines
            continue
            
        # Count financial keywords in this chunk
        keyword_count = sum(1 for keyword in financial_keywords 
                          if keyword.lower() in chunk.lower())
        
        # Include chunks with financial keywords or numbers
        if keyword_count > 0 or re.search(r'\d{1,3}(?:,\d{3})*', chunk):
            relevant_chunks.append(chunk)
    
    # Return most relevant sections (limit to avoid token limits)
    financial_text = '\n'.join(relevant_chunks[:100])  # Increased to 100 lines
    
    # If we didn't find much financial content, return cleaned original
    if len(financial_text) < 500:
        return text[:3000]  # First 3000 chars of cleaned text
    
    return financial_text


def extract_text_from_sections(text_sections: List[TextSection]) -> str:
    """
    Extract and combine text content from TextSection objects with cleaning
    """
    combined_text = ""
    
    for section in text_sections:
        if section.content and section.content.strip():
            # Skip sections that are just whitespace or coordinates
            if len(section.content.strip()) > 10:  # Only meaningful content
                combined_text += section.content + "\n"
    
    # Apply comprehensive text cleaning
    cleaned_text = clean_ocr_text(combined_text)
    
    # Extract most relevant financial sections
    financial_text = extract_financial_context(cleaned_text)
    
    print(f"DEBUG - Original text: {len(combined_text)} chars")
    print(f"DEBUG - Cleaned text: {len(cleaned_text)} chars") 
    print(f"DEBUG - Financial text: {len(financial_text)} chars")
    print(f"DEBUG - Sample cleaned text: {financial_text[:500]}...")
    
    return financial_text

async def extract_financial_metrics_with_gpt4(text: str) -> FinancialData:
    """
    Enhanced GPT-4 extraction with comprehensive XML-structured prompt
    Optimized for UK football club financial statements
    """
    
    if not API_KEY:
        logger.error("Azure AI API key not configured")
        raise HTTPException(status_code=500, detail="Azure AI API key not configured")
    
    # Basic validation
    if not text or len(text.strip()) < 10:
        logger.warning(f"Insufficient text for extraction: {len(text) if text else 0} characters")
        return FinancialData()
    
    try:
        # Document type detection
        document_info = detect_abridged_accounts(text)
        
        logger.info("Starting enhanced financial extraction",
                   text_length=len(text),
                   is_abridged=document_info["is_abridged"],
                   document_type=document_info["document_type"],
                   profit_loss_filed=document_info["profit_loss_filed"])
        
        client = AzureOpenAI(
            api_version=API_VERSION,
            azure_endpoint=ENDPOINT,
            api_key=API_KEY,
        )
        
        # Comprehensive XML-structured prompt
        xml_prompt = f"""<context>
You are a UK Chartered Accountant (ACA/ACCA) with specialized expertise in football club financial statements. You have deep knowledge of:
- UK GAAP (FRS 102) and Companies Act 2006 statutory requirements
- Football-specific accounting including player registrations as intangible assets
- EFL Financial Fair Play regulations and reporting standards
- UK statutory filing formats including small company exemptions and abridged accounts
- Championship, League One, and League Two financial patterns and benchmarks
</context>

<financial_document>
{text}
</financial_document>

<critical_knowledge>
<uk_account_types>
- Full Statutory Accounts: Complete P&L, Balance Sheet, Cash Flow, and Notes
- Abridged Accounts: Balance Sheet only, filed under small companies regime (Section 444)
- Micro-Entity Accounts: Simplified balance sheet format with minimal disclosure
</uk_account_types>

<football_context>
- Player registrations appear as "Intangible assets" or "Intangible fixed assets"
- Player sales show as "Profit/(loss) on disposal of registrations" - this is NOT revenue
- Championship broadcasting revenue typically £7-12M, League One £1.5-2.5M
- Total staff costs typically represent 60-100% of turnover in football
- Wage ratios exceeding 80% often indicate financial strain
</football_context>

<uk_profit_loss_structure>
Standard UK Football P&L Format (from actual data patterns):

BASIC STRUCTURE:
Turnover (main revenue line)
Cost of sales
Gross profit/(loss)
Administrative expenses
Operating profit/(loss) ← Key metric
Interest receivable and similar income
Interest payable and similar expenses
Profit/(loss) before taxation
Tax on profit/(loss)
Profit/(loss) for the financial year ← Net income

FOOTBALL-SPECIFIC VARIATIONS:
- Some clubs separate "Administrative expenses before player amortisation" then add "Player amortisation and impairment"
- Some show "Operations excluding player trading" vs "Player trading" columns
- "Profit on disposal of registrations" appears separately (player sale profits)
- "Other operating income" often includes grants and other non-core income

OTHER COMPREHENSIVE INCOME (if present):
- Revaluation gains/losses on property
- Tax on other comprehensive income
Total comprehensive income/(expense) for the year
</uk_profit_loss_structure>

<uk_balance_sheet_structure>
Standard UK Format (most common):
FIXED ASSETS
  Intangible assets (usually player registrations)
  Tangible assets (stadium, training ground, equipment)
  Investments
  [Fixed Assets Total - often not explicitly shown]

CURRENT ASSETS  
  Stocks/Inventories
  Debtors (including amounts due after more than one year)
  Cash at bank and in hand
  [Current Assets Total - may be shown as subtotal]

CREDITORS: Amounts falling due within one year (negative)
NET CURRENT LIABILITIES (usually negative)
TOTAL ASSETS LESS CURRENT LIABILITIES ← CRITICAL: This is NOT total assets!
CREDITORS: Amounts falling due after more than one year (negative)
PROVISIONS FOR LIABILITIES (negative)
NET ASSETS/(LIABILITIES) (can be negative = "Net liabilities")

CAPITAL AND RESERVES
  Called up share capital
  Share premium
  Revaluation reserve
  Profit and loss reserves (often negative)
  TOTAL EQUITY (equals Net Assets/Liabilities)
</uk_balance_sheet_structure>

<uk_cash_flow_structure>
Standard UK Football Cash Flow Format (from actual data):

CASH FLOWS FROM OPERATING ACTIVITIES:
- Loss/Profit before taxation (starting point)
- Add back: Depreciation on property, plant and equipment
- Add back: Amortisation of intangible assets (player amortisation)
- Remove: Profit on disposal of players' registrations
- Add back: Finance costs/expenses
- Working capital changes:
  * (Increase)/Decrease in inventories
  * (Increase)/Decrease in trade and other receivables
  * Increase/(Decrease) in trade and other payables
- Interest paid/received
- Taxation received/paid
Net cash from operating activities

CASH FLOWS FROM INVESTING ACTIVITIES:
- Purchase of property, plant and equipment
- Purchase of intangible fixed assets (player purchases)
- Proceeds from disposal of players' registrations (player sales)
- Sale of tangible fixed assets
Net cash from investing activities

CASH FLOWS FROM FINANCING ACTIVITIES:
- Proceeds from borrowings/loans received
- Repayment of borrowings
- Directors'/shareholders' loans
- Issue of share capital
- Finance lease payments
- Interest paid
Net cash from financing activities

Net increase/(decrease) in cash and cash equivalents
Cash and cash equivalents at beginning of year
Cash and cash equivalents at end of year
</uk_cash_flow_structure>

<key_notes_structure>
Critical Notes to Extract From (based on actual football data):

NOTE: TURNOVER ANALYSIS
- Gate receipts/Match receipts/Matchday income
- Broadcasting/Media income/EFL distributions
- Commercial income/Sponsorship/Other commercial
- Other revenue streams

NOTE: INTANGIBLE ASSETS (Player Registrations)
- Cost brought forward
- Additions (new player purchases)
- Disposals (player sales)
- Amortisation charge for the year
- Impairment charges (if any)
- Net book value at year end

NOTE: STAFF COSTS
- Wages and salaries
- Social security costs
- Pension costs
- Playing staff vs non-playing staff breakdown (if disclosed)

NOTE: OPERATING LOSS/PROFIT
- Breakdown of administrative expenses
- Player amortisation and impairment details
- Exceptional items
- Operating lease charges
- Depreciation charges

NOTE: RELATED PARTY TRANSACTIONS
- Transactions with directors/owners
- Inter-company transactions
- Loans from/to related parties
</key_notes_structure>
</critical_knowledge>

<extraction_rules>
<step_1_document_classification>
MANDATORY FIRST TASK: Determine account type.

Set is_abridged to TRUE if ANY of these indicators appear:
- Explicit phrase "abridged accounts" or "abridged balance sheet"
- Reference to "Section 444" of the Companies Act 2006
- Declaration "small companies regime" 
- Statement "directors have chosen not to file profit & loss account"
- No Profit & Loss statement present, only Balance Sheet
- Text indicates "small company exemption"

Set document_type based on classification:
- "abridged": No P&L filed, balance sheet only
- "micro": Simplified micro-entity format
- "full": Complete statutory accounts with P&L

If is_abridged is true, most P&L fields will be null.
</step_1_document_classification>

<step_2_scale_detection>
CRITICAL: Identify scale used throughout document before extracting ANY numbers.

Scan document headers, column headers, and footnotes for scale indicators:

Scale Pattern Recognition:
- "£'000", "£000", "thousands", "000s" → ALL figures must be multiplied by 1,000
- "£m", "millions", "Million" → ALL figures must be multiplied by 1,000,000  
- "£" only with 7+ digit numbers → Use figures as-is (full amounts)
- "£" only with 4-5 digit numbers → Likely thousands, check context

Set scale_indicator field:
- "thousands": if £'000 indicators found
- "millions": if £m indicators found  
- "full": if large numbers without scale indicators
- "mixed": if inconsistent (flag for review)

Consistency Rule: ALL monetary values in same document must use same scale conversion.

Examples:
- Document shows "£'000" and "Turnover: 32,271" → Extract as 32,271,000
- Document shows "£" and "Turnover: 32,271,000" → Extract as 32,271,000
</step_2_scale_detection>

<step_3_balance_sheet_assets>
Calculate total_assets using PRIORITY ORDER:

Priority 1: Look for explicit "Total assets" line (rare in UK format)

Priority 2: UK STANDARD CALCULATION (most common):
- Identify Fixed Assets section total OR sum: Intangible + Tangible + Investments
- Identify Current Assets section total OR sum: Stocks + Debtors + Cash
- Calculate: total_assets = Fixed Assets + Current Assets

Priority 3: Component sum fallback:
- total_assets = intangible_assets + tangible_assets + current_assets

CRITICAL RULE: NEVER use "Total assets less current liabilities" as total_assets
This is a UK balance sheet subtotal, NOT total assets.

Set balance_sheet_format:
- "uk_standard": No explicit total assets, requires calculation
- "explicit_totals": Total assets explicitly stated
- "complex": Non-standard format requiring interpretation
</step_3_balance_sheet_assets>

<step_4_balance_sheet_liabilities>
Calculate total_liabilities using PRIORITY ORDER:

Priority 1: Look for explicit "Total liabilities" (very rare)

Priority 2: Balance Sheet Equation (preferred method):
- If Net Assets positive: total_liabilities = total_assets - net_assets
- If Net Liabilities: total_liabilities = total_assets + |net_liabilities|

Priority 3: Creditor sum (backup only):
- Sum: creditors_due_within_one_year + creditors_due_after_one_year + provisions

Balance Sheet Validation:
- Must satisfy: Total Assets = Total Liabilities + Total Equity
- If equation doesn't balance within £1,000, flag as error
</step_4_balance_sheet_liabilities>

<step_5_profit_loss_extraction>
Only extract if is_abridged is FALSE.

net_income PRIORITY ORDER (extract pure business performance):
1. "Loss/Profit for the financial year" (preferred - operational result)
2. "Loss/Profit for the year"
3. "Net profit/loss"  
4. "Total comprehensive loss/income" (backup only - includes revaluations)

Ensure losses are negative values: (9,589) → -9589000

operating_profit extraction:
- "Operating profit" OR "Operating loss" (make losses negative)
- Line appears before interest and taxation
- Key performance indicator for football clubs

Revenue components (from Turnover note):
- turnover: "Turnover", "Revenue", "Total income" from P&L header
- matchday_revenue: "Gate receipts", "Match receipts", "Match day income", "Season tickets", "Matchday"
- broadcasting_revenue: "Broadcasting", "EFL distributions", "Central distributions", "Media"  
- commercial_revenue: "Commercial", "Sponsorship", "Merchandising", "Retail", "Other commercial"

Validation: matchday + broadcasting + commercial should ≈ turnover (within 15% tolerance)
</step_5_profit_loss_extraction>

<step_6_football_specific>
Player-related extractions (key football metrics):

player_amortization:
- "Player amortisation" OR "Amortisation of intangible assets"  
- "Player amortisation and impairment"
- Usually largest expense item after wages
- Make negative: represents expense

player_trading_income:
- "Profit on disposal of registrations" 
- "Profit on disposal of players"
- "Profit/(loss) on sale of intangible assets"
- IMPORTANT: This is disposal profit, NOT revenue

player_wages:
- "Playing staff costs" OR "Players' remuneration"
- "Player wages" (if separately disclosed)
- Usually 60-80% of total staff costs

Asset recognition:
- intangible_assets: Usually represents player registrations in football context
- Player registrations typically 80-95% of total intangible assets for football clubs
</step_6_football_specific>

<step_7_cash_flow_extraction>
Only extract if cash flow statement is present:

operating_cash_flow:
- "Net cash from operating activities"
- "Cash flows from operating activities" (net figure)
- Starting from loss before taxation, adjusted for non-cash items

investing_cash_flow:
- "Net cash from investing activities"
- Includes player purchases (outflow) and player sales (inflow)
- Purchase of intangible/tangible assets

financing_cash_flow:
- "Net cash from financing activities"
- Loan receipts/repayments, share issues, finance costs
</step_7_cash_flow_extraction>

<step_8_validation_checks>
Apply these consistency checks:

Balance Sheet Equation:
- Total Assets = Total Liabilities + Total Equity
- Allow £1,000 tolerance for rounding
- Flag major discrepancies

Revenue Logic:
- Matchday + Broadcasting + Commercial ≈ Turnover (within 15%)
- Broadcasting revenue benchmarks:
  * Championship: £7-12M typically
  * League One: £1.5-2.5M typically
  * League Two: Under £1.5M typically

Scale Consistency:
- All extracted figures should reflect same scale conversion
- Flag if turnover seems unreasonably small (may indicate scale error)

Football Industry Sanity Checks:
- Total staff costs usually 60-100% of turnover
- Player wages usually 60-80% of total staff costs
- Operating losses are common but check for reasonableness
</step_8_validation_checks>
</extraction_rules>

<number_processing_rules>
Negative Value Recognition:
- Numbers in parentheses are NEGATIVE: (1,234) → -1,234
- Apply negative sign before scale conversion: (1,234) in £'000 → -1,234,000

Scale Application:
- Apply scale conversion to ALL monetary values consistently
- Examples:
  * £'000 scale + figure 32,271 → 32,271,000
  * £m scale + figure 32.3 → 32,300,000
  * Full amounts + figure 32,271,000 → 32,271,000

Null vs Zero:
- Use null for fields not found or not applicable
- Use 0 for explicitly stated zero values
- Use null for all P&L fields if is_abridged is true
</number_processing_rules>

<output_format>
Return a valid JSON object with this exact structure. All monetary values must be in full British Pounds (not thousands or millions):

{{
  "is_abridged": boolean,
  "document_type": "full" | "abridged" | "micro",
  "scale_indicator": "thousands" | "millions" | "full" | "mixed" | null,
  "balance_sheet_format": "uk_standard" | "explicit_totals" | "complex" | null,
  "company_name": string | null,
  "accounting_year_end": "YYYY-MM-DD" | null,
  
  // Profit & Loss Statement (null if abridged)
  "turnover": number | null,
  "operating_profit": number | null,
  "net_income": number | null,
  "profit_before_tax": number | null,
  "profit_for_the_year": number | null,
  "cost_of_sales": number | null,
  "gross_profit": number | null,
  "gross_loss": number | null,
  "administrative_expenses": number | null,
  "interest_receivable": number | null,
  "interest_payable": number | null,
  "other_operating_income": number | null,
  
  // Revenue Breakdown (from notes)
  "matchday_revenue": number | null,
  "broadcasting_revenue": number | null,
  "commercial_revenue": number | null,
  
  // Balance Sheet - Assets
  "total_assets": number | null,
  "intangible_assets": number | null,
  "tangible_assets": number | null,
  "current_assets": number | null,
  "stocks": number | null,
  "debtors": number | null,
  "cash_at_bank": number | null,
  "cash_and_cash_equivalents": number | null,
  
  // Balance Sheet - Liabilities & Equity
  "total_liabilities": number | null,
  "creditors_due_within_one_year": number | null,
  "creditors_due_after_one_year": number | null,
  "net_assets": number | null,
  "total_equity": number | null,
  
  // Football-Specific Metrics
  "player_amortization": number | null,
  "player_trading_profit": number | null,
  "player_wages": number | null,
  "profit_on_player_disposals": number | null,
  "loss_on_player_disposals": number | null,
  
  // Staff Costs (from notes)
  "staff_costs_total": number | null,
  "social_security_costs": number | null,
  "pension_costs": number | null,
  
  // Other Operating Items
  "depreciation_charges": number | null,
  "operating_lease_charges": number | null,
  
  // Cash Flow (if present)
  "operating_cash_flow": number | null,
  "investing_cash_flow": number | null,
  "financing_cash_flow": number | null,
  
  // Legacy fields for compatibility
  "revenue": number | null,
  "operating_expenses": number | null,
  "profit_loss_before_tax": number | null,
  "player_trading_income": number | null,
  "total_staff_costs": number | null,
  "other_staff_costs": number | null,
  "stadium_costs": number | null,
  "agent_fees": number | null
}}
</output_format>

<critical_reminders>
1. SCALE CONVERSION: Apply scale consistently to ALL monetary values
2. NEGATIVE VALUES: Numbers in parentheses are negative
3. UK BALANCE SHEET: "Total assets less current liabilities" ≠ total assets
4. BALANCE EQUATION: Total Assets must equal Total Liabilities + Total Equity
5. FOOTBALL CONTEXT: Player registrations are intangible assets, not revenue when sold
6. ABRIDGED ACCOUNTS: Set most P&L fields to null if is_abridged is true
7. NULL VALUES: Use null for missing data, not zero
8. VALIDATION: Check that revenue components sum to turnover within reasonable tolerance
</critical_reminders>"""
        
        # Enhanced GPT-4 call with XML prompt
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "user", "content": xml_prompt}
            ],
            temperature=0.01,  # Extremely low for maximum consistency
            max_tokens=3000,   # Increased for comprehensive response
            response_format={{"type": "json_object"}}
        )
        
        result_text = response.choices[0].message.content
        print(f"GPT-4 raw response: {{result_text}}")
        logger.info(f"GPT-4 extraction completed with XML prompt", 
                   extra={"response_length": len(result_text),
                  "estimated_cost_tokens": response.usage.total_tokens if hasattr(response, 'usage') else 'unknown'})
        
        # Parse and validate JSON response
        try:
            financial_dict = json.loads(result_text)
            
            print(f"DEBUG - Before validation: operating_expenses = {{financial_dict.get('operating_expenses')}}")
            print(f"DEBUG - Before validation: net_income = {{financial_dict.get('net_income')}}")  
            print(f"DEBUG - Before validation: total_equity = {{financial_dict.get('total_equity')}}")
            
            # Validate extracted values
            validated_dict = validate_financial_data(financial_dict)
            
            print(f"DEBUG - After validation: operating_expenses = {{validated_dict.get('operating_expenses')}}")
            print(f"DEBUG - After validation: net_income = {{validated_dict.get('net_income')}}")
            print(f"DEBUG - After validation: total_equity = {{validated_dict.get('total_equity')}}")
            
            # Create FinancialData object with all fields
            result = FinancialData(
                # Document metadata from detection
                is_abridged=document_info["is_abridged"],
                document_type=document_info["document_type"],
                profit_loss_filed=document_info["profit_loss_filed"],
                
                # Financial data from extraction with enhanced mapping
                revenue=validated_dict.get('revenue') or validated_dict.get('turnover'),
                turnover=validated_dict.get('turnover'),
                operating_expenses=validated_dict.get('operating_expenses'),
                total_equity=validated_dict.get('total_equity'),               
                net_income=validated_dict.get('net_income'),                  
                total_assets=validated_dict.get('total_assets'),
                total_liabilities=validated_dict.get('total_liabilities'),
                net_assets=validated_dict.get('net_assets'),
                cash_at_bank=validated_dict.get('cash_at_bank'),
                cash_and_cash_equivalents=validated_dict.get('cash_and_cash_equivalents'),
                creditors_due_within_one_year=validated_dict.get('creditors_due_within_one_year'),
                creditors_due_after_one_year=validated_dict.get('creditors_due_after_one_year'),
                operating_profit=validated_dict.get('operating_profit'),
                profit_loss_before_tax=validated_dict.get('profit_loss_before_tax') or validated_dict.get('profit_before_tax'),
                broadcasting_revenue=validated_dict.get('broadcasting_revenue'),
                commercial_revenue=validated_dict.get('commercial_revenue'),
                matchday_revenue=validated_dict.get('matchday_revenue'),
                player_trading_income=validated_dict.get('player_trading_income') or validated_dict.get('player_trading_profit'),
                player_wages=validated_dict.get('player_wages'),
                player_amortization=validated_dict.get('player_amortization'),
                other_staff_costs=validated_dict.get('other_staff_costs'),
                stadium_costs=validated_dict.get('stadium_costs'),
                administrative_expenses=validated_dict.get('administrative_expenses'),
                agent_fees=validated_dict.get('agent_fees'),
                cost_of_sales=validated_dict.get('cost_of_sales'),
                gross_profit=validated_dict.get('gross_profit'),
                gross_loss=validated_dict.get('gross_loss'),
                interest_receivable=validated_dict.get('interest_receivable'),
                interest_payable=validated_dict.get('interest_payable'),
                other_operating_income=validated_dict.get('other_operating_income'),
                staff_costs_total=validated_dict.get('staff_costs_total') or validated_dict.get('total_staff_costs'),
                social_security_costs=validated_dict.get('social_security_costs'),
                pension_costs=validated_dict.get('pension_costs'),
                depreciation_charges=validated_dict.get('depreciation_charges'),
                operating_lease_charges=validated_dict.get('operating_lease_charges'),
                profit_on_player_disposals=validated_dict.get('profit_on_player_disposals'),
                loss_on_player_disposals=validated_dict.get('loss_on_player_disposals'),
                intangible_assets=validated_dict.get('intangible_assets'),
                tangible_assets=validated_dict.get('tangible_assets'),
                current_assets=validated_dict.get('current_assets'),
                stocks=validated_dict.get('stocks'),
                debtors=validated_dict.get('debtors'),
                operating_cash_flow=validated_dict.get('operating_cash_flow'),
                investing_cash_flow=validated_dict.get('investing_cash_flow'),
                financing_cash_flow=validated_dict.get('financing_cash_flow'),
            )
            
            print(f"DEBUG - Final result: operating_expenses = {{result.operating_expenses}}")
            print(f"DEBUG - Final result: net_income = {{result.net_income}}")
            print(f"DEBUG - Final result: total_equity = {{result.total_equity}}")
            
            # Enhanced logging with XML prompt context
            extracted_fields = [k for k, v in validated_dict.items() if v is not None]
            logger.info("Enhanced financial extraction successful",
                       extra={"fields_extracted": len(extracted_fields),
                            "extracted_fields": extracted_fields[:10],
                            "is_abridged": document_info["is_abridged"],
                            "document_type": document_info["document_type"],
                            "scale_indicator": validated_dict.get('scale_indicator'),
                            "balance_sheet_format": validated_dict.get('balance_sheet_format')})
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("JSON parsing failed", error=str(e), response_preview=result_text[:200])
            return FinancialData()
            
    except Exception as e:
        logger.error("Enhanced financial extraction failed", extra={"error": str(e), "error_type": type(e).__name__})
        return FinancialData()


def detect_abridged_accounts(text: str) -> Dict[str, Any]:
    """
    Helper function to detect if financial statements are abridged accounts
    Returns document type information and filing status
    """
    text_lower = text.lower()
    
    # Initialize detection results
    detection_result = {
        "is_abridged": False,
        "document_type": "unknown",
        "profit_loss_filed": None,
        "filing_exemptions": []
    }
    
    # PRIMARY DETECTION: Look for "unaudited abridged accounts" in title
    # This is the most reliable indicator as it appears in every abridged filing
    if "unaudited abridged accounts" in text_lower:
        detection_result["is_abridged"] = True
        detection_result["document_type"] = "abridged"
        detection_result["profit_loss_filed"] = False  # Abridged accounts don't include P&L
        logger.info("Detected abridged accounts from title", 
                   indicator="unaudited abridged accounts")
        return detection_result
    
    # SECONDARY DETECTION: Other abridged indicators as fallback
    abridged_indicators = [
        "abridged accounts",
        "abridged financial statements", 
        "preparation of abridged accounts",
        "section 444",
        "section 444(2a)",
        "section 444 (2a)",  # With spaces
        "small companies regime"
    ]
    
    # Check for other abridged account indicators
    for indicator in abridged_indicators:
        if indicator in text_lower:
            detection_result["is_abridged"] = True
            detection_result["document_type"] = "abridged"
            detection_result["profit_loss_filed"] = False
            logger.info("Detected abridged accounts from indicator", 
                       indicator=indicator)
            return detection_result
    
    # Check for micro entity accounts (even more limited than abridged)
    micro_indicators = [
        "micro-entity",
        "micro entity",
        "section 384a",
        "section 384b"
    ]
    
    for indicator in micro_indicators:
        if indicator in text_lower:
            detection_result["is_abridged"] = True
            detection_result["document_type"] = "micro"
            detection_result["profit_loss_filed"] = False
            logger.info("Detected micro entity accounts", 
                       indicator=indicator)
            return detection_result
    
    # If not abridged, check for full accounts with exemptions
    small_company_indicators = [
        "section 477",
        "small companies",
        "small company exemption",
        "audit exemption"
    ]
    
    for indicator in small_company_indicators:
        if indicator in text_lower:
            detection_result["filing_exemptions"].append("small_company")
    
    # Check if Profit & Loss Account appears to be present (for full accounts)
    profit_loss_present_indicators = [
        "profit and loss account",
        "statement of comprehensive income",
        "income statement",
        "turnover"
    ]
    
    profit_loss_present = any(indicator in text_lower for indicator in profit_loss_present_indicators)
    
    # Determine final classification for non-abridged accounts
    if profit_loss_present:
        detection_result["document_type"] = "full"
        detection_result["profit_loss_filed"] = True
    else:
        detection_result["document_type"] = "unknown"
        detection_result["profit_loss_filed"] = None
    
    logger.info("Document type detection completed",
               is_abridged=detection_result["is_abridged"],
               document_type=detection_result["document_type"],
               profit_loss_filed=detection_result["profit_loss_filed"],
               exemptions=detection_result["filing_exemptions"])
    
    return detection_result


def validate_financial_data(financial_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted financial data for business logic consistency
    """
    validated = {}
    
    for key, value in financial_dict.items():
        if value is None:
            validated[key] = None
            continue
            
        # Convert to float and validate
        try:
            numeric_value = float(value) if value != 0 else 0.0
            
            # Basic sanity checks for football club finances
            if key in ['revenue', 'turnover', 'total_assets']:
                # These should be positive for operating clubs
                if numeric_value < 0:
                    logger.warning(f"Unusual negative value for {key}: {numeric_value}")
                    
            elif key in ['total_liabilities', 'creditors_due_within_one_year']:
                # These are typically positive (amounts owed)
                if numeric_value < 0:
                    logger.warning(f"Unusual negative liability for {key}: {numeric_value}")
                    
            elif key == 'cash_at_bank':
                # Can be negative (overdraft) so no validation needed
                pass
                
            # Range validation for football clubs
            if key in ['revenue', 'turnover'] and numeric_value > 500000000:  # £500M+
                logger.warning(f"Unusually high {key} for football club: {numeric_value}")
                
            validated[key] = numeric_value
            
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {key} value to number: {value}")
            validated[key] = None
    
    return validated




        
@router.post("/extract-financials", response_model=SkillResponse)
async def extract_financials(request: SkillRequest):
    """
    Azure Search Custom Web API Skill endpoint - handles TextSection objects
    """
    print(f"DEBUG - Received extract-financials request with {len(request.values)} values")
    
    if not API_KEY:
        raise HTTPException(status_code=500, detail="Azure AI API key not configured")
    
    results = []
    
    for i, value in enumerate(request.values):
        record_id = value.recordId
        print(f"DEBUG - Processing record {i}: {record_id}")
        
        # Handle both text_sections array and simple text
        text_content = ""
        
        if value.data.text_sections:
            print(f"DEBUG - Found {len(value.data.text_sections)} text sections")
            text_content = extract_text_from_sections(value.data.text_sections)
            print(f"DEBUG - Combined into {len(text_content)} characters")
            print(f"DEBUG - Text preview: {text_content[:200]}...")
            
        elif value.data.text:
            print(f"DEBUG - Found simple text: {len(value.data.text)} characters")
            text_content = value.data.text
            
        else:
            print(f"DEBUG - No text content found for {record_id}")
            results.append(RecordResult(
                recordId=record_id,
                data=FinancialData(),
                errors=[RecordError(message="No text content provided")]
            ))
            continue
        
        # ENHANCED: Fix for West Brom whitespace issue
        if text_content and (text_content.count('\n') > len(text_content) * 0.8 or len(text_content.strip()) < 100):
            print(f"DEBUG - Content appears to be mostly whitespace/newlines, trying text_sections fallback")
            if value.data.text_sections:
                print(f"DEBUG - Attempting fallback extraction from {len(value.data.text_sections)} text sections")
                text_content = extract_text_from_sections(value.data.text_sections)
                print(f"DEBUG - Fallback extracted {len(text_content)} characters")
                print(f"DEBUG - Fallback preview: {text_content[:200]}...")
            else:
                print(f"DEBUG - No text_sections available for fallback")
        
        if not text_content.strip():
            print(f"DEBUG - Empty text content for {record_id}")
            results.append(RecordResult(
                recordId=record_id,
                data=FinancialData(),
                errors=[RecordError(message="Empty text content")]
            ))
            continue
        
        try:
            print(f"DEBUG - Starting extraction for {record_id}")
            financial_data = await extract_financial_metrics_with_gpt4(text_content)
            
            results.append(RecordResult(
                recordId=record_id,
                data=financial_data
            ))
            
            print(f"DEBUG - Successfully extracted for {record_id}: {financial_data}")
            
        except Exception as e:
            print(f"DEBUG - Error extracting for {record_id}: {e}")
            results.append(RecordResult(
                recordId=record_id,
                data=FinancialData(),
                errors=[RecordError(message=f"Extraction failed: {str(e)}")]
            ))
    
    print(f"DEBUG - Returning {len(results)} results")
    return SkillResponse(values=results)

@router.post("/test-extraction")
async def test_extraction(request: InputData):
    """Test endpoint for development"""
    
    if not API_KEY:
        raise HTTPException(status_code=500, detail="Azure AI API key not configured")
    
    # Handle both formats in test endpoint too
    if request.text_sections:
        text_content = extract_text_from_sections(request.text_sections)
        print(f"DEBUG - Test: Combined {len(request.text_sections)} sections into {len(text_content)} characters")
    elif request.text:
        text_content = request.text
        print(f"DEBUG - Test: Using {len(text_content)} characters of text")
    else:
        raise HTTPException(status_code=400, detail="No text provided")
    
    try:
        result = await extract_financial_metrics_with_gpt4(text_content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check for financial extraction service"""
    return {
        "status": "healthy",
        "service": "financial-extraction", 
        "model": DEPLOYMENT,
        "endpoint": ENDPOINT,
        "api_key_configured": bool(API_KEY)
    }
    
    
@router.get("/health/comprehensive-processing")
async def health_check_comprehensive():
    """Health check for comprehensive document processing service"""
    
    try:
        from app.services.document_intelligence.client import DocumentIntelligenceService
        
        # Test Document Intelligence connection
        doc_service = DocumentIntelligenceService()
        
        return {
            "status": "healthy",
            "service": "comprehensive-document-processing",
            "document_intelligence": {
                "endpoint": doc_service.endpoint,
                "configured": bool(doc_service.key)
            },
            "azure_openai": {
                "configured": bool(os.environ.get("AZURE_AI_FOUNDRY_API_KEY"))
            },
            "components": {
                "document_intelligence": "available",
                "text_cleaning": "available", 
                "metadata_extraction": "available",
                "financial_extraction": "available"
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }