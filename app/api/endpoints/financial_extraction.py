
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from openai import AzureOpenAI
import json
import os
import logging

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

class RecordError(BaseModel):
    message: str

class RecordResult(BaseModel):
    recordId: str
    data: FinancialData
    errors: Optional[List[RecordError]] = None

class SkillResponse(BaseModel):
    values: List[RecordResult]

def extract_text_from_sections(text_sections: List[TextSection]) -> str:
    """
    Extract and combine text content from TextSection objects
    """
    combined_text = ""
    
    for section in text_sections:
        # section is already a TextSection object, just get the content
        combined_text += section.content + " "
    
    return combined_text.strip()

async def extract_financial_metrics_with_gpt4(text: str) -> FinancialData:
    """
    Use GPT-4.1 via Azure OpenAI to extract financial figures from club accounts text
    """
    
    if not API_KEY:
        print("DEBUG - No API key configured!")
        raise HTTPException(status_code=500, detail="Azure AI API key not configured")
    
    try:
        print(f"DEBUG - Using GPT-4.1 for extraction from {len(text)} characters")
        print(f"DEBUG - Text preview: {text[:300]}...")
        
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            api_version=API_VERSION,
            azure_endpoint=ENDPOINT,
            api_key=API_KEY,
        )
        
        # Precise prompt for GPT-4.1
        system_prompt = """You are a financial data extraction expert. Extract specific numbers from UK football club balance sheets and return only valid JSON."""
        
        user_prompt = f"""Extract financial numbers from this UK football club balance sheet text:

{text[:1500]}

Find these exact items and return ONLY this JSON format:
{{
    "cash_at_bank": number_or_null,
    "net_assets": number_or_null,
    "total_assets": number_or_null,
    "creditors_due_within_one_year": number_or_null,
    "turnover": number_or_null,
    "operating_profit": number_or_null
}}

Rules:
- Look for: "Cash at bank", "Net assets", "Total assets", "Creditors amounts falling due", "Turnover", "Operating profit/loss"
- Numbers only (no £, commas): "12,345" becomes 12345
- Parentheses mean negative: "(1,788,978)" becomes -1788978
- Return null if not found
- Return ONLY the JSON, no explanation"""

        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_completion_tokens=300,
            temperature=0.0,  # Very deterministic for consistent extraction
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            model=DEPLOYMENT
        )
        
        content = response.choices[0].message.content.strip()
        print(f"DEBUG - GPT-4.1 response: '{content}'")
        
        # Extract and parse JSON
        if '{' in content and '}' in content:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_content = content[json_start:json_end]
            print(f"DEBUG - Extracted JSON: '{json_content}'")
            
            financial_dict = json.loads(json_content)
            print(f"DEBUG - Parsed successfully: {financial_dict}")
            
            # Map to all FinancialData fields
            result = FinancialData(
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
                profit_loss_before_tax=financial_dict.get('profit_loss_before_tax')
            )
            
            return result
        else:
            print(f"DEBUG - No JSON found in response")
            return FinancialData()
            
    except json.JSONDecodeError as e:
        print(f"DEBUG - JSON parsing error: {e}")
        return FinancialData()
    except Exception as e:
        print(f"DEBUG - GPT-4.1 error: {type(e).__name__}: {e}")
        return FinancialData()
    finally:
        # Close the client if it was created
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