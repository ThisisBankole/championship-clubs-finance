import os
from typing import List, Dict, Any
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from app.services.cache.redis_cache import cache_result
import structlog

logger = structlog.get_logger()

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
    
    @cache_result(ttl=3600, key_prefix="clubs_search")  
    async def search_with_club_info(self, query: str = "*") -> List[Dict[str, Any]]:
        """Search clubs - data is already structured by Azure AI Search"""
        if not self.search_client:
            return [{"error": "Azure Search not configured"}]
        
        try:
            logger.info("Executing Azure Search query", query=query)
            results = self.search_client.search(
                search_text=query,
                top=50,
            )
            
            # Data is already clean from your custom skill!
            search_results = [dict(result) for result in results]
            logger.info("Azure Search completed", query=query, results_count=len(search_results))
            return search_results
            
        except Exception as e:
            logger.error("Azure Search failed", query=query, error=str(e))
            return [{"error": f"Search failed: {str(e)}"}]