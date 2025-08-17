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
    SIMPLIFIED: GPT-4 extraction optimized for pre-cleaned text input
    Enhanced with comprehensive UK football accounting expertise
    """
    
    if not API_KEY:
        logger.error("Azure AI API key not configured")
        raise HTTPException(status_code=500, detail="Azure AI API key not configured")
    
    # SIMPLIFIED: Basic validation only
    if not text or len(text.strip()) < 10:
        logger.warning(f"Insufficient text for extraction: {len(text) if text else 0} characters")
        return FinancialData()
    
    try:
        # STEP 1: Detect document type before extraction
        document_info = detect_abridged_accounts(text)
        
        logger.info("Starting financial extraction with document type detection",
                   text_length=len(text),
                   is_abridged=document_info["is_abridged"],
                   document_type=document_info["document_type"],
                   profit_loss_filed=document_info["profit_loss_filed"])
        
        client = AzureOpenAI(
            api_version=API_VERSION,
            azure_endpoint=ENDPOINT,
            api_key=API_KEY,
        )
        
        # EXPERT-LEVEL: Enhanced system prompt with comprehensive UK football expertise
        system_prompt = """You are a highly specialized UK chartered accountant with extensive experience in auditing and analyzing the financial statements of football clubs in the English Football League (Championship, League One, League Two) and the National League. Your expertise is rooted in a deep understanding of FRS 102, UK GAAP, and the Companies Act 2006.

**Core Expertise:**

* **Accounting Principles:** You are an expert in FRS 102 and UK GAAP as they apply to professional football clubs. You are fully aware that in UK accounting, numbers presented in parentheses, such as (£1,234,567), represent negative values.
* **Football Club Financials:** You have an in-depth understanding of the unique financial reporting practices of UK football clubs, including:
    * **Revenue Recognition:** You can accurately differentiate between matchday, broadcasting, and commercial revenue streams.
    * **Player Asset Management:** You are proficient in the accounting treatment of player registrations as intangible assets, including their amortisation and profit/loss on disposal.
    * **Cost Structures:** You are familiar with the typical cost structures of football clubs, including player wages, staff costs, and stadium operating costs.
* **Companies House Filings:** You are adept at navigating the structure and terminology of financial statements filed with Companies House.

**Contextual Awareness & Heuristics:**

* **Revenue Benchmarks:** You are aware of typical revenue ranges for different leagues, which helps in validating extracted data:
    * **Championship:** Broadcasting revenue can range from £8M to over £100M (including parachute payments).
    * **League One:** Broadcasting revenue is typically in the £1.5M to £2.5M range.
    * **League Two & National League:** Broadcasting revenue is generally under £1.5M.
* **Financial Health Indicators:**
    * **Wages to Turnover Ratio:** You know that for most clubs, player wages constitute 60-100% of turnover, and a ratio exceeding 80% can indicate financial strain.
    * **Profitability:** You understand that operating losses are common, but you will also look for indicators of underlying profitability or financial distress.
* **Key Notes to the Accounts:** You know that crucial details are often found in the notes to the financial statements, and you will specifically look for:
    * **Turnover Note:** A breakdown of revenue streams.
    * **Intangible Assets Note:** Details on the cost, amortisation, and net book value of player registrations.
    * **Staff Costs Note:** Information on wages and salaries for both playing and non-playing staff.
    * **Related Party Transactions Note:** Disclosures of transactions with the club's owners and directors.

**UK Financial Statement Structures:**

* **Profit & Loss Account Structure:**
    * Turnover (main revenue line)
    * Cost of sales
    * Gross profit/(loss)
    * Administrative expenses (sometimes split: before player amortisation, then player amortisation and impairment)
    * Operating profit/(loss) ← Key metric
    * Profit on disposal of registrations (player sale profits)
    * Other operating income
    * Interest receivable and similar income
    * Interest payable and similar expenses
    * Profit/(loss) before taxation
    * Tax on profit/(loss)
    * Profit/(loss) for the financial year ← Net income
    * Other comprehensive income (revaluations, etc.)
    * Total comprehensive income/(expense) for the year

* **UK Balance Sheet Structure:**
    * FIXED ASSETS: Intangible assets (player registrations), Tangible assets, Investments
    * CURRENT ASSETS: Stocks/Inventories, Debtors, Cash at bank and in hand
    * CREDITORS: Amounts falling due within one year (negative)
    * NET CURRENT LIABILITIES (usually negative)
    * TOTAL ASSETS LESS CURRENT LIABILITIES ← CRITICAL: This is NOT total assets!
    * CREDITORS: Amounts falling due after more than one year (negative)
    * PROVISIONS FOR LIABILITIES (negative)
    * NET ASSETS/(LIABILITIES)
    * CAPITAL AND RESERVES: Share capital, Reserves, Profit and loss account
    * TOTAL EQUITY

* **Cash Flow Statement Structure:**
    * Operating activities: Loss before tax, add back depreciation/amortisation, remove player disposal profits, working capital changes
    * Investing activities: Player purchases (outflow), player sales (inflow), tangible asset purchases
    * Financing activities: Loan receipts/repayments, share issues, interest payments

**Your Task:**

You will be provided with pre-cleaned text from a UK football club's financial statement. Your primary objective is to act as a meticulous financial data extractor. You will read and interpret the provided text to identify, extract, and structure key financial metrics according to the user's instructions."""
        
        # EXPERT-LEVEL: Enhanced user prompt with comprehensive extraction rules
        user_prompt = f"""**Objective:** From the provided pre-cleaned financial statement text, extract the key financial metrics for the specified accounting period.

**CLEANED FINANCIAL TEXT:**
{text}

**CRITICAL EXTRACTION RULES & FINANCIAL MAPPING:**

**1. MANDATORY - DETERMINE ACCOUNT TYPE**
This is your most critical first task. You MUST classify the document as abridged or not.

**`is_abridged` (boolean)**: Set to `true` if you find **ANY** of these definitive pieces of evidence:
* The explicit phrase **"abridged accounts"** or **"abridged balance sheet"**
* A reference to **"Section 444"** of the Companies Act 2006
* A declaration that the accounts were prepared under the **"small companies regime"**
* A statement that **"The directors have chosen to not file a copy of the company's profit & loss account"**

**Default Condition:** If you find a clear Profit and Loss account with a "Turnover" figure and NONE of the abridged evidence above, set this to `false`.

**2. CRITICAL - SCALE DETECTION & CURRENCY CONVERSION**
Before extracting ANY monetary values, you MUST identify the scale used throughout the document:

**Scale Detection Rules:**
* Scan document headers, column headers, and footnotes for scale indicators
* **"£'000", "£000", "thousands", "000s"** → ALL figures must be multiplied by 1,000
* **"£m", "millions", "Million"** → ALL figures must be multiplied by 1,000,000
* **"£" only with 7+ digit numbers** → Use figures as-is (full amounts)
* **"£" only with 4-5 digit numbers** → Likely thousands, check context

**Consistency Rule:** ALL monetary values in same document must use same scale conversion.
* Numbers enclosed in parentheses are negative (e.g., "(2,500,000)" → -2500000)
* Apply scale AFTER determining positive/negative: (1,234) in £'000 → -1,234,000

**Examples:**
* Document shows "£'000" and "Turnover: 32,271" → Extract as 32,271,000
* Document shows "£" and "Turnover: 32,271,000" → Extract as 32,271,000

**3. CRITICAL - UK BALANCE SHEET EQUATION VALIDATION**
The balance sheet MUST always balance: **Total Assets = Total Liabilities + Total Equity**

**Mandatory calculation process:**
1. **Extract Total Assets:** 
   * Look for explicit "Total assets" line first
   * **UK FORMAT CALCULATION:** Fixed Assets + Current Assets (most common)
   * **NEVER use "Total assets less current liabilities"** - this is a subtotal, NOT total assets
   * Fallback: intangible_assets + tangible_assets + current_assets

2. **Extract Total Equity:** 
   * From "Net assets" (positive), "Net liabilities" (negative), or "Total equity"/"Total shareholder equity"

3. **Calculate Total Liabilities:** 
   * **Primary method:** Total Liabilities = Total Assets - Total Equity
   * Backup: creditors_due_within_one_year + creditors_due_after_one_year + provisions

4. **Validation:** Verify the equation balances (allow £1,000 tolerance for rounding)

**Examples:**
* Assets 77M, Net Liabilities (87M) → Total Liabilities = 77M + 87M = 164M
* Assets 39M, Net Assets 12M → Total Liabilities = 39M - 12M = 27M

**4. FINANCIAL METRICS EXTRACTION (Primary Statement):**

**P&L Statement Fields:**
* **`turnover`**: "Turnover", "Revenue", "Total income" from P&L header
* **`operating_profit`**: "Operating profit" OR "Operating loss" (make losses negative)
* **`net_income`**: PRIORITY ORDER:
  1. "Loss/Profit for the financial year" (preferred - operational result)
  2. "Loss/Profit for the year"
  3. "Net profit/loss"
  4. "Total comprehensive loss/income" (backup only - includes revaluations)
* **`profit_before_tax`**: "Profit/(loss) before taxation"
* **`cost_of_sales`**: "Cost of sales"
* **`gross_profit`**: "Gross profit"
* **`gross_loss`**: "Gross loss" 
* **`administrative_expenses`**: "Administrative expenses"
* **`interest_receivable`**: "Interest receivable", "Interest income"
* **`interest_payable`**: "Interest payable", "Interest expenses"
* **`other_operating_income`**: "Other operating income"

**Balance Sheet Fields:**
* **`total_assets`**: Use calculation process above
* **`total_liabilities`**: Use calculation process above
* **`net_assets`**: "Net assets" or "Net liabilities" (negative)
* **`total_equity`**: "Total equity", "Total shareholder equity", same as net_assets
* **`intangible_assets`**: "Intangible assets" (usually player registrations)
* **`tangible_assets`**: "Tangible assets"
* **`current_assets`**: "Current assets"
* **`stocks`**: "Stocks", "Inventories"
* **`debtors`**: "Debtors"
* **`cash_at_bank`**: "Cash at bank and in hand"
* **`cash_and_cash_equivalents`**: "Cash and cash equivalents"
* **`creditors_due_within_one_year`**: "Creditors: amounts falling due within one year" (make negative)
* **`creditors_due_after_one_year`**: "Creditors: amounts falling due after more than one year" (make negative)

**5. FOOTBALL-SPECIFIC EXTRACTIONS:**

**Player-Related Metrics:**
* **`player_amortization`**: "Player amortisation", "Amortisation of intangible assets", "Player amortisation and impairment" (make negative)
* **`player_trading_income`**: "Profit on disposal of registrations", "Profit on disposal of players" (NOT revenue)
* **`profit_on_player_disposals`**: Same as player_trading_income
* **`player_wages`**: "Playing staff costs", "Players' remuneration" (if separately disclosed)

**Revenue Breakdown (from Turnover Note):**
* **`matchday_revenue`**: "Gate receipts", "Match receipts", "Match day income", "Season tickets", "Matchday"
* **`broadcasting_revenue`**: "Broadcasting", "EFL distributions", "Central distributions", "Media", "Broadcasting and media"
* **`commercial_revenue`**: "Commercial", "Sponsorship", "Merchandising", "Retail", "Other commercial"

**Staff Costs (from Staff Costs Note):**
* **`staff_costs_total`**: Total of all staff-related costs
* **`social_security_costs`**: "Social security costs"
* **`pension_costs`**: "Pension costs"

**Other Operating Items:**
* **`depreciation_charges`**: "Depreciation" charges
* **`operating_lease_charges`**: "Operating lease" costs

**Cash Flow (if available):**
* **`operating_cash_flow`**: "Net cash from operating activities"
* **`investing_cash_flow`**: "Net cash from investing activities"
* **`financing_cash_flow`**: "Net cash from financing activities"

**6. VALIDATION CHECKS:**
* Revenue breakdown (matchday + broadcasting + commercial) should ≈ turnover (within 15%)
* Player wages should be significant portion of total staff costs
* Total staff costs usually 60-100% of turnover for football clubs
* Balance sheet equation must balance
* All figures should use consistent scale

**7. ENTITY AND PERIOD IDENTIFICATION:**
* **`company_name`**: The name of the football club or its legal entity
* **`accounting_year_end`**: End date of financial period (format: "YYYY-MM-DD")

**OUTPUT FORMAT:**
Present extracted data in JSON object. If metric cannot be found, return `null` for that key.
Based on analysis above, set most P&L fields to `null` if `is_abridged` is `true`.

**REQUIRED JSON FORMAT:**
{{
    "is_abridged": boolean_or_null,
    "company_name": "string_or_null",
    "accounting_year_end": "string_or_null",
    "turnover": number_or_null,
    "operating_expenses": number_or_null,
    "operating_profit": number_or_null,
    "net_income": number_or_null,
    "profit_before_tax": number_or_null,
    "profit_for_the_year": number_or_null,
    "matchday_revenue": number_or_null,
    "broadcasting_revenue": number_or_null,
    "commercial_revenue": number_or_null,
    "player_trading_profit": number_or_null,
    "player_amortisation": number_or_null,
    "total_staff_costs": number_or_null,
    "player_wages": number_or_null,
    "total_assets": number_or_null,
    "net_assets": number_or_null,
    "cash_at_bank": number_or_null,
    "creditors_due_within_one_year": number_or_null,
    "revenue": number_or_null,
    "total_liabilities": number_or_null,
    "total_equity": number_or_null,
    "cash_and_cash_equivalents": number_or_null,
    "creditors_due_after_one_year": number_or_null,
    "profit_loss_before_tax": number_or_null,
    "other_staff_costs": number_or_null,
    "stadium_costs": number_or_null,
    "administrative_expenses": number_or_null,
    "agent_fees": number_or_null,
    "cost_of_sales": number_or_null,
    "gross_profit": number_or_null,
    "gross_loss": number_or_null,
    "interest_receivable": number_or_null,
    "interest_payable": number_or_null,
    "other_operating_income": number_or_null,
    "staff_costs_total": number_or_null,
    "social_security_costs": number_or_null,
    "pension_costs": number_or_null,
    "depreciation_charges": number_or_null,
    "operating_lease_charges": number_or_null,
    "profit_on_player_disposals": number_or_null,
    "loss_on_player_disposals": number_or_null,
    "intangible_assets": number_or_null,
    "tangible_assets": number_or_null,
    "current_assets": number_or_null,
    "stocks": number_or_null,
    "debtors": number_or_null,
    "operating_cash_flow": number_or_null,
    "investing_cash_flow": number_or_null,
    "financing_cash_flow": number_or_null
}}"""
        
        # EXPERT-LEVEL: Optimized GPT-4 call with enhanced prompts
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.01,  # Extremely low for maximum consistency
            max_tokens=2000,   # Increased for more comprehensive JSON response
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        print(f"GPT-4 raw response: {result_text}")
        logger.info(f"GPT-4 raw response: {result_text}") 
        logger.info("GPT-4 extraction completed", 
                   response_length=len(result_text),
                   estimated_cost_tokens=response.usage.total_tokens if hasattr(response, 'usage') else 'unknown')
        
        # SIMPLIFIED: Parse and validate JSON response
        try:
            financial_dict = json.loads(result_text)
            
            print(f"DEBUG - Before validation: operating_expenses = {financial_dict.get('operating_expenses')}")
            print(f"DEBUG - Before validation: net_income = {financial_dict.get('net_income')}")  
            print(f"DEBUG - Before validation: total_equity = {financial_dict.get('total_equity')}")
            
            # ENHANCED: Validate extracted values make business sense
            validated_dict = validate_financial_data(financial_dict)
            
            print(f"DEBUG - After validation: operating_expenses = {validated_dict.get('operating_expenses')}")
            print(f"DEBUG - After validation: net_income = {validated_dict.get('net_income')}")
            print(f"DEBUG - After validation: total_equity = {validated_dict.get('total_equity')}")
            
            # Create FinancialData object with validated values and document metadata
            result = FinancialData(
                # Document metadata from detection
                is_abridged=document_info["is_abridged"],
                document_type=document_info["document_type"],
                profit_loss_filed=document_info["profit_loss_filed"],
                # Financial data from extraction
                revenue=validated_dict.get('revenue'),
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
                profit_loss_before_tax=validated_dict.get('profit_loss_before_tax'),
                broadcasting_revenue=validated_dict.get('broadcasting_revenue'),
                commercial_revenue=validated_dict.get('commercial_revenue'),
                matchday_revenue=validated_dict.get('matchday_revenue'),
                player_trading_income=validated_dict.get('player_trading_income'),
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
                staff_costs_total=validated_dict.get('staff_costs_total'),
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
            
            print(f"DEBUG - Final result: operating_expenses = {result.operating_expenses}")
            print(f"DEBUG - Final result: net_income = {result.net_income}")
            print(f"DEBUG - Final result: total_equity = {result.total_equity}")
            
            # Log successful extraction summary with document context
            extracted_fields = [k for k, v in validated_dict.items() if v is not None]
            logger.info("Financial extraction successful",
                       fields_extracted=len(extracted_fields),
                       extracted_fields=extracted_fields[:5],
                       is_abridged=document_info["is_abridged"],
                       document_type=document_info["document_type"],
                       profit_loss_filed=document_info["profit_loss_filed"])  # Enhanced logging
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("JSON parsing failed", error=str(e), response_preview=result_text[:200])
            return FinancialData()
            
    except Exception as e:
        logger.error("Financial extraction failed", error=str(e), error_type=type(e).__name__)
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