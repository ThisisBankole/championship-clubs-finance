from fastapi import APIRouter
from app.services.scheduler.championship_scheduler import ChampionshipScheduler

router = APIRouter()
scheduler = ChampionshipScheduler()

@router.post("/start")
async def start_scheduler():
    """Start the championship data scheduler"""
    scheduler.start_scheduler()
    return {"status": "Scheduler started"}

@router.post("/stop")
async def stop_scheduler():
    """Stop the championship data scheduler"""
    scheduler.stop_scheduler()
    return {"status": "Scheduler stopped"}

@router.post("/trigger-now")
async def trigger_update_now():
    """Manually trigger championship data update"""
    scheduler.update_championship_data()
    return {"status": "Update triggered"}