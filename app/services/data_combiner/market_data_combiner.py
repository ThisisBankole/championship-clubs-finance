import json
import structlog
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os

logger = structlog.get_logger()

class MarketDataCombiner:
    def __init__(self):
        self.storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.search_endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        self.search_key = os.getenv('AZURE_SEARCH_KEY')
        self.index_name = "financial-index"
        self.eur_to_gbp_rate = None
        
        
    def get_exchange_rate(self):
        """Get live EUR to GBP exchange rate"""
        try:
            # Free API - no key required
            response = requests.get('https://api.exchangerate-api.com/v4/latest/EUR')
            data = response.json()
            rate = data['rates']['GBP']
            
            logger.info(f"Retrieved EUR/GBP rate: {rate}")
            return rate
            
        except Exception as e:
            logger.error("Failed to get exchange rate, using fallback", error=str(e))
            return 0.85  # Fallback rate

    def get_market_data(self):
        """Read market data from blob storage"""
        blob_service = BlobServiceClient.from_connection_string(self.storage_connection)
        blob_client = blob_service.get_blob_client("clubs-fin", "market-data/latest/championship-table.json")
        
        content = blob_client.download_blob().readall()
        market_records = []
        
        # Parse JSONL format
        for line in content.decode().strip().split('\n'):
            if line:
                market_records.append(json.loads(line))
        
        return market_records
    
    def get_financial_data(self):
        """Read financial data from search index"""
        credential = AzureKeyCredential(self.search_key)
        search_client = SearchClient(self.search_endpoint, self.index_name, credential)
        
        results = search_client.search("*", select="*")
        return list(results)
    
    def match_clubs(self, financial_data, market_data):
        """Match and combine financial and market data"""
        
               
        if not self.eur_to_gbp_rate:
            self.eur_to_gbp_rate = self.get_exchange_rate()
            
            
        combined_records = []
        
        logger.info("Starting club matching", 
               financial_count=len(financial_data), 
               market_count=len(market_data))
        
        for financial_record in financial_data:
            club_name = financial_record.get("club_name") or ""
            
            # Find matching market record
            market_record = None
            normalized_financial_name = self.normalize_name(club_name)
            
            logger.info("Processing financial club", 
            original_name=club_name, 
            normalized_name=normalized_financial_name)
            
            market_record = None
            
            for market in market_data:
                market_name = market.get("name") or ""
                normalized_market_name = self.normalize_name(market_name)
                
                logger.info("Comparing with market club", 
                       market_original=market_name, 
                       market_normalized=normalized_market_name,
                       financial_normalized=normalized_financial_name,
                       match=normalized_market_name == normalized_financial_name)

                
                if normalized_market_name == normalized_financial_name:
                    market_record = market
                    logger.info("MATCH FOUND!", 
                           financial_club=club_name, 
                           market_club=market_name)
                    break
                
                if not market_record:
                    logger.warning("NO MATCH FOUND", financial_club=club_name)
            
            # Add market fields to financial record
            if market_record:
                financial_record["current_market_value_eur"] = market_record.get("total_market_value")
                financial_record["current_market_value_gbp"] = int(market_record.get("total_market_value", 0) * self.eur_to_gbp_rate)
                financial_record["market_value_change"] = market_record.get("market_value_change")
                financial_record["championship_position"] = market_record.get("championship_position")
                financial_record["transfermarkt_id"] = market_record.get("transfermarkt_id")
                
            
            combined_records.append(financial_record)
        
        return combined_records
    
    def normalize_name(self, name):
        """Normalize club names for matching"""
        if not name:
            return ""
        
        
        normalized = name.lower()
        
        suffixes_to_remove = [" afc", " fc", " ltd", " limited", " football club", " association football club"]
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
            
        normalized = normalized.strip()
        return normalized
    
    def update_search_index(self, combined_data):
        """Upload combined data to search index"""
        credential = AzureKeyCredential(self.search_key)
        search_client = SearchClient(self.search_endpoint, self.index_name, credential)
        
        search_client.upload_documents(combined_data)
        logger.info("Updated search index with market data", count=len(combined_data))
    
    def combine_data(self):
        """Main method to combine financial and market data"""
        try:
            market_data = self.get_market_data()
            financial_data = self.get_financial_data()
            
            combined_data = self.match_clubs(financial_data, market_data)
            self.update_search_index(combined_data)
            
            return {"status": "success", "updated_records": len(combined_data)}
            
        except Exception as e:
            logger.error("Data combination failed", error=str(e))
            return {"status": "error", "message": str(e)}