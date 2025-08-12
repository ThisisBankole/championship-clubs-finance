from fastapi import APIRouter, HTTPException
import structlog
import subprocess
import time
from app.services.data_combiner.market_data_combiner import MarketDataCombiner

logger = structlog.get_logger()
router = APIRouter()

@router.post("/update-championship-data")
async def update_championship_data():
    """Complete Championship data update pipeline"""
    
    try:
        logger.info("Starting championship data update pipeline")
        
        # Step 1: Trigger Azure Container Instance
        logger.info("Triggering Championship scraper container")
        container_result = trigger_championship_scraper()
        
        if not container_result["success"]:
            raise HTTPException(status_code=500, detail=f"Container failed: {container_result['error']}")
        
        # Step 2: Wait for container completion
        logger.info("Waiting for container completion")
        wait_for_container_completion()
        
        # Step 3: Run data combiner
        logger.info("Combining financial and market data")
        combiner = MarketDataCombiner()
        result = combiner.combine_data()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        logger.info("Championship data update pipeline completed successfully")
        return {
            "status": "success",
            "container_execution": container_result,
            "data_combination": result,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Championship data update pipeline failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

def trigger_championship_scraper():
    """Trigger Azure Container Instance"""
    try:
        # Delete existing container if exists
        delete_cmd = [
            "az", "container", "delete",
            "--resource-group", "transfermarkt-rg",
            "--name", "championship-scraper-blob",
            "--yes"
        ]
        subprocess.run(delete_cmd, capture_output=True)
        
        # Create new container
        create_cmd = [
            "az", "container", "create",
            "--resource-group", "transfermarkt-rg", 
            "--name", "championship-scraper-blob",
            "--image", "btransfermarktregistry.azurecr.io/transfermarkt-enhanced:latest",
            "--registry-login-server", "btransfermarktregistry.azurecr.io",
            "--registry-username", "btransfermarktregistry",
            "--registry-password", "9/3yS6LX7tlvFY1BOi5JmyThmNl5ZJE1caKxfpVOBA+ACRABGuQ0",
            "--restart-policy", "Never",
            "--os-type", "Linux",
            "--cpu", "1",
            "--memory", "1",
            "--environment-variables",
            "AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=clubfin;AccountKey=hA1BaPUCUAFFki1tEFGCpzLqaTAQ/G6T6OII4m2/Tv+NRPEHL+sJ0n4IJCVcFIICSTt1GZmK58JB+AStuq05kA==;EndpointSuffix=core.windows.net",
            "AZURE_STORAGE_CONTAINER=clubs-fin",
            "--command-line", "sh -c 'scrapy crawl championship_table -s USER_AGENT=\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\" && python upload_to_blob.py'",
            "--location", "westeurope"
        ]
        
        result = subprocess.run(create_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"success": True, "message": "Container created successfully"}
        else:
            return {"success": False, "error": result.stderr}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def wait_for_container_completion():
    """Wait for container to complete execution"""
    max_wait = 300  # 5 minutes
    check_interval = 10  # 10 seconds
    elapsed = 0
    
    while elapsed < max_wait:
        try:
            status_cmd = [
                "az", "container", "show",
                "--resource-group", "transfermarkt-rg",
                "--name", "championship-scraper-blob",
                "--query", "instanceView.state",
                "--output", "tsv"
            ]
            
            result = subprocess.run(status_cmd, capture_output=True, text=True)
            state = result.stdout.strip()
            
            if state in ["Succeeded", "Failed", "Terminated"]:
                logger.info(f"Container completed with state: {state}")
                return
                
            time.sleep(check_interval)
            elapsed += check_interval
            
        except Exception as e:
            logger.error("Error checking container status", error=str(e))
            break
    
    logger.warning("Container wait timeout reached")

@router.post("/combine-market-data")
async def combine_market_data():
    """Combine financial and market data in search index"""
    
    try:
        combiner = MarketDataCombiner()
        result = combiner.combine_data()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        logger.info("Market data combination completed", result=result)
        return result
        
    except Exception as e:
        logger.error("Market data combination failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/debug-club-names")
async def debug_club_names():
    """Debug club name matching"""
    
    combiner = MarketDataCombiner()
    
    # Get both datasets
    market_data = combiner.get_market_data()
    financial_data = combiner.get_financial_data()
    
    # Extract names
    market_names = [m.get("name") for m in market_data]
    financial_names = [f.get("club_name") for f in financial_data]
    
    return {
        "market_names": market_names,
        "financial_names": financial_names,
        "market_count": len(market_names),
        "financial_count": len(financial_names)
    }
    
@router.get("/debug-market-data")
async def debug_market_data():
    """Debug market data from blob"""
    
    combiner = MarketDataCombiner()
    market_data = combiner.get_market_data()
    
    # Find Wrexham specifically
    wrexham_data = None
    for market in market_data:
        if market and "wrexham" in str(market.get("name", "")).lower():
            wrexham_data = market
            break
    
    return {
        "total_market_records": len(market_data),
        "wrexham_found": wrexham_data is not None,
        "wrexham_data": wrexham_data,
        "first_few_records": market_data[:3]
    }
    
@router.get("/debug-normalize")
async def debug_normalize():
    """Debug name normalization"""
    
    combiner = MarketDataCombiner()
    
    test_names = [
        "Wrexham AFC",
        "Wrexham", 
        "Southampton FC",
        "Southampton",
        "Portsmouth FC",
        "Portsmouth"
    ]
    
    results = {}
    for name in test_names:
        results[name] = combiner.normalize_name(name)
    
    return results