
import structlog
from typing import Dict, List

logger = structlog.get_logger()

class ClubMetadataExtractor:
    """Extracts club metadata from blob storage paths"""
    
    def extract_from_blob_path(self, blob_path: str) -> Dict[str, str]:
        """Your existing extraction logic as a service method"""
        try:
            if 'clubs-fin/' in blob_path:
                path_part = blob_path.split('clubs-fin/')[1]
            else:
                path_part = blob_path
                
            parts = path_part.split('/')
            if len(parts) >= 2:
                folder = parts[0]
                date_folder = parts[1]
                
                if '-' in folder:
                    company_number = folder.split('-')[0]
                    club_name = folder.split('-', 1)[1].replace('-', ' ').title()
                    
                    return {
                        "company_number": company_number,
                        "club_name": club_name,
                        "accounts_year_end": date_folder
                    }
            
            return {
                "company_number": "",
                "club_name": "Unknown",
                "accounts_year_end": ""
            }
            
        except Exception as e:
            logger.error("Metadata extraction failed", blob_path=blob_path, error=str(e))
            return {
                "company_number": "",
                "club_name": "Error", 
                "accounts_year_end": ""
            }
    
    def process_azure_search_request(self, request_data: Dict) -> Dict:
        """Process Azure AI Search skillset request format"""
        values = request_data.get('values', [])
        results = []
        
        for record in values:
            blob_path = record.get('data', {}).get('blob_path', '')
            record_id = record.get('recordId', '')
            
            club_info = self.extract_from_blob_path(blob_path)
            
            result = {
                "recordId": record_id,
                "data": club_info,
                "errors": [],
                "warnings": []
            }
            results.append(result)
        
        return {"values": results}