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
    revenue: Optional[float] = None
    turnover: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
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
    Enhanced GPT-4.1 extraction for both basic and Championship-level football finance
    """
    
    if not API_KEY:
        print("DEBUG - No API key configured!")
        raise HTTPException(status_code=500, detail="Azure AI API key not configured")
    
    try:
        print(f"DEBUG - Using enhanced football finance analysis for {len(text)} characters")
        
        client = AzureOpenAI(
            api_version=API_VERSION,
            azure_endpoint=ENDPOINT,
            api_key=API_KEY,
        )
        
        # Enhanced system prompt for football finance
        system_prompt = """You are a football finance analyst specializing in UK football club financial statements. You understand both basic accounting and advanced football-specific financial categorization including player registrations, transfer accounting, and football revenue streams."""
        
        # Enhanced user prompt that extracts both basic and advanced metrics
        user_prompt = f"""Extract financial data from this UK football club balance sheet and profit & loss statement as a football finance expert. Extract the key business performance indicators that investors and analysts use to evaluate football clubs:
        
        IMPORTANT: This text has OCR formatting issues. Look for patterns like:
        - "Cash at bank123,456" means "Cash at bank: 123,456"
        - "PROFIT BEFORE TAXATION3,334,238" means "PROFIT BEFORE TAXATION: 3,334,238"
        - Numbers in parentheses are negative: "(20,895,263)" = -20,895,263

{text[:2000]}

Look for BOTH basic financial metrics AND football-specific categories:

BASIC METRICS:
- Cash at bank/Cash and cash equivalents
- Net assets/Net liabilities  
- Total assets
- Creditors due within one year
- Turnover/Revenue
- Operating profit

FOOTBALL-SPECIFIC METRICS:
- Broadcasting revenue: "Central distributions", "EFL payments", "Media rights", "Parachute payments"
- Commercial revenue: "Sponsorship", "Commercial partnerships", "Advertising"
- Matchday revenue: "Gate receipts", "Season tickets", "Match day income"
- Player trading income: "Profit on disposal of players' registrations", "Transfer fees"
- Player wages: "Players' remuneration", "Playing staff salaries"
- Player amortization: "Amortisation of players' registrations"
- Other staff costs: "Administrative staff", "Management" (exclude players)
- Stadium costs: "Ground expenses", "Stadium maintenance"
- Administrative expenses: "Professional fees", "Travel", "Insurance"
- Agent fees: "Agent commissions", "Intermediary fees"

FOOTBALL BUSINESS INTELLIGENCE:
- Championship clubs typically receive £7-12M broadcasting (unless parachute payments = £30-40M)
- Player wages usually 60-80% of total revenue
- Transfer profits can be £0-50M+ in a single year
- Matchday revenue depends on stadium size (10k-40k capacity)

EXAMPLES FROM REAL ACCOUNTS:
- "Central distributions from The Football League £8.2M" = Broadcasting Revenue
- "Amortisation of players' registrations £3.1M" = Player Amortization  
- "Profit on disposal of registrations £15.3M" = Player Trading Income
- "Players' remuneration £22.8M" = Player Wages

Return this exact JSON format:
{{
    "revenue": number_or_null,
    "turnover": number_or_null,
    "total_assets": number_or_null,
    "total_liabilities": number_or_null,
    "net_assets": number_or_null,
    "cash_at_bank": number_or_null,
    "cash_and_cash_equivalents": number_or_null,
    "creditors_due_within_one_year": number_or_null,
    "creditors_due_after_one_year": number_or_null,
    "operating_profit": number_or_null,
    "profit_loss_before_tax": number_or_null,
    "broadcasting_revenue": number_or_null,
    "commercial_revenue": number_or_null,
    "matchday_revenue": number_or_null,
    "player_trading_income": number_or_null,
    "player_wages": number_or_null,
    "player_amortization": number_or_null,
    "other_staff_costs": number_or_null,
    "stadium_costs": number_or_null,
    "administrative_expenses": number_or_null,
    "agent_fees": number_or_null
}}

CRITICAL: Think like a football investor analyzing a football business, not a generic accountant. Use football industry knowledge to interpret accounts correctly.

Rules: Numbers only (no £, commas). Parentheses = negative. null if not found."""

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=600, 
            temperature=0.0,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            model=DEPLOYMENT
        )
        
        content = response.choices[0].message.content.strip()
        print(f"DEBUG - Enhanced GPT-4.1 response: '{content}'")
        
        # Extract and parse JSON
        if '{' in content and '}' in content:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_content = content[json_start:json_end]
            
            financial_dict = json.loads(json_content)
            print(f"DEBUG - Parsed enhanced financial data: {financial_dict}")
            
            # Map to ALL FinancialData fields (both old and new)
            result = FinancialData(
                # Original fields
                revenue=financial_dict.get('revenue'),
                turnover=financial_dict.get('turnover'),
                total_assets=financial_dict.get('total_assets'),
                total_liabilities=financial_dict.get('total_liabilities'),
                net_assets=financial_dict.get('net_assets'),
                cash_at_bank=financial_dict.get('cash_at_bank'),
                cash_and_cash_equivalents=financial_dict.get('cash_and_cash_equivalents'),
                creditors_due_within_one_year=financial_dict.get('creditors_due_within_one_year'),
                creditors_due_after_one_year=financial_dict.get('creditors_due_after_one_year'),
                operating_profit=financial_dict.get('operating_profit'),
                profit_loss_before_tax=financial_dict.get('profit_loss_before_tax'),
                
                # New Championship fields
                broadcasting_revenue=financial_dict.get('broadcasting_revenue'),
                commercial_revenue=financial_dict.get('commercial_revenue'),
                matchday_revenue=financial_dict.get('matchday_revenue'),
                player_trading_income=financial_dict.get('player_trading_income'),
                player_wages=financial_dict.get('player_wages'),
                player_amortization=financial_dict.get('player_amortization'),
                other_staff_costs=financial_dict.get('other_staff_costs'),
                stadium_costs=financial_dict.get('stadium_costs'),
                administrative_expenses=financial_dict.get('administrative_expenses'),
                agent_fees=financial_dict.get('agent_fees')
            )
            
            return result
        else:
            print(f"DEBUG - No JSON found in response")
            return FinancialData()
            
    except json.JSONDecodeError as e:
        print(f"DEBUG - JSON parsing error: {e}")
        return FinancialData()
    except Exception as e:
        print(f"DEBUG - Enhanced extraction error: {type(e).__name__}: {e}")
        return FinancialData()
    finally:
        try:
            client.close()
        except:
            pass
        
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