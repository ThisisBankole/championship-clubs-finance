
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import structlog

from app.services.azure_search.manager import AzureSearchManager

logger = structlog.get_logger()
router = APIRouter()

@router.post("/create-data-source")
async def create_data_source():
    """Step 1: Create Azure Search data source"""
    try:
        manager = AzureSearchManager()
        result = manager.create_data_source()
        
        return {
            "status": "success",
            "message": f"Data source created: {result}",
            "resource_name": result
        }
        
    except Exception as e:
        logger.error("Failed to create data source", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-index")
async def create_index():
    """Step 2: Create Azure Search index"""
    try:
        manager = AzureSearchManager()
        result = manager.create_search_index()
        
        return {
            "status": "success", 
            "message": f"Search index created: {result}",
            "resource_name": result
        }
        
    except Exception as e:
        logger.error("Failed to create index", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-skillset")
async def create_skillset(use_combined_extraction: bool = True):
    """Step 3: Create Azure Search skillset"""
    try:
        manager = AzureSearchManager()
        result = manager.create_skillset(use_combined_extraction=use_combined_extraction)
        
        return {
            "status": "success",
            "message": f"Skillset created: {result}",
            "resource_name": result,
            "combined_extraction": use_combined_extraction
        }
        
    except Exception as e:
        logger.error("Failed to create skillset", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-indexer")
async def create_indexer():
    """Step 4: Create Azure Search indexer"""
    try:
        manager = AzureSearchManager()
        result = manager.create_indexer()
        
        return {
            "status": "success",
            "message": f"Indexer created: {result}",
            "resource_name": result
        }
        
    except Exception as e:
        logger.error("Failed to create indexer", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-all")
async def create_all_resources():
    """Create all Azure Search resources in correct order"""
    try:
        manager = AzureSearchManager()
        results = {}
        
        # Step 1: Data Source
        logger.info("Creating data source...")
        results["data_source"] = manager.create_data_source()
        
        # Step 2: Index
        logger.info("Creating index...")
        results["index"] = manager.create_search_index()
        
        # Step 3: Skillset
        logger.info("Creating skillset...")
        results["skillset"] = manager.create_skillset(use_combined_extraction=True)
        
        # Step 4: Indexer
        logger.info("Creating indexer...")
        results["indexer"] = manager.create_indexer()
        
        return {
            "status": "success",
            "message": "All Azure Search resources created successfully",
            "resources": results
        }
        
    except Exception as e:
        logger.error("Failed to create all resources", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run-indexer")
async def run_indexer():
    """Run the indexer to process documents"""
    try:
        manager = AzureSearchManager()
        success = manager.run_indexer()
        
        if success:
            return {
                "status": "success",
                "message": "Indexer started successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start indexer")
            
    except Exception as e:
        logger.error("Failed to run indexer", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indexer-status")
async def get_indexer_status():
    """Get current indexer status"""
    try:
        manager = AzureSearchManager()
        status = manager.get_indexer_status()
        
        return {
            "status": "success",
            "indexer_status": status
        }
        
    except Exception as e:
        logger.error("Failed to get indexer status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-all")
async def delete_all_resources():
    """Delete all Azure Search resources (cleanup)"""
    try:
        manager = AzureSearchManager()
        manager.delete_all_resources()
        
        return {
            "status": "success",
            "message": "All Azure Search resources deleted"
        }
        
    except Exception as e:
        logger.error("Failed to delete resources", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recreate-all")
async def recreate_all_resources():
    """Delete existing resources and create new ones"""
    try:
        manager = AzureSearchManager()
        
        # Delete existing resources
        logger.info("Deleting existing resources...")
        manager.delete_all_resources()
        
        # Wait a moment for deletion to complete
        import asyncio
        await asyncio.sleep(5)
        
        # Create new resources
        logger.info("Creating new resources...")
        results = {}
        results["data_source"] = manager.create_data_source()
        results["index"] = manager.create_search_index()
        results["skillset"] = manager.create_skillset(use_combined_extraction=True)
        results["indexer"] = manager.create_indexer()
        
        return {
            "status": "success",
            "message": "All Azure Search resources recreated successfully",
            "resources": results
        }
        
    except Exception as e:
        logger.error("Failed to recreate resources", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))