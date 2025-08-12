import schedule
import time
import threading
import structlog
import requests
from datetime import datetime

logger = structlog.get_logger()

class ChampionshipScheduler:
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url
        self.running = False
        self.thread = None
    
    def update_championship_data(self):
        """Call the championship data update endpoint"""
        try:
            logger.info("Scheduled championship data update starting")
            
            response = requests.post(f"{self.api_base_url}/api/v1/data-combiner/update-championship-data")
            
            if response.status_code == 200:
                logger.info("Scheduled championship data update completed successfully")
            else:
                logger.error("Scheduled championship data update failed", 
                           status_code=response.status_code, 
                           response=response.text)
                
        except Exception as e:
            logger.error("Scheduled championship data update error", error=str(e))
    
    def start_scheduler(self):
        """Start the scheduler"""
        if self.running:
            return
        
        # Schedule for 1st and 15th of each month at 3 AM
        schedule.every().day.at("03:00").tag("championship").do(self._check_and_run)
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("Championship scheduler started - runs 1st and 15th at 3 AM")
    
    def _check_and_run(self):
        """Check if today is 1st or 15th and run update"""
        today = datetime.now().day
        if today in [1, 15]:
            self.update_championship_data()
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear("championship")
        logger.info("Championship scheduler stopped")