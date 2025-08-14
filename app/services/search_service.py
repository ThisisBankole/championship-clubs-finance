import os
from typing import List, Dict, Any
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

class FinancialSearchService:
    def __init__(self):
        endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        key = os.getenv('AZURE_SEARCH_KEY')
        index_name = os.getenv('AZURE_SEARCH_INDEX_NAME', 'financial-index')
        
        if endpoint and key:
            self.search_client = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=AzureKeyCredential(key)
            )
        else:
            self.search_client = None
    
    async def search_with_club_info(self, query: str = "*") -> List[Dict[str, Any]]:
        """Search clubs - data is already structured by Azure AI Search"""
        if not self.search_client:
            return [{"error": "Azure Search not configured"}]
        
        try:
            results = self.search_client.search(
                search_text=query,
                top=50,
                
            )
            
            # Data is already clean from your custom skill!
            return [dict(result) for result in results]
            
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]