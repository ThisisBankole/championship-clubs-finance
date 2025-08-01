"""
Data models for club financial information
"""

from typing import Optional
from pydantic import BaseModel


class ClubFinancialData(BaseModel):
    """Model for club financial filing data"""
    
    club_name: str
    company_number: str
    legal_name: Optional[str] = None
    filing_date: Optional[str] = None
    accounts_year_end: Optional[str] = None
    filing_year: Optional[str] = None
    description: Optional[str] = None
    pdf_uploaded: Optional[bool] = False
    status: str = "pending"
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True