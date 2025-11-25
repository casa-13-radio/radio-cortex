# api/routes/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone

from models.database import get_session

router = APIRouter()

@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    """
    Health check endpoint for load balancers and monitoring.
    """
    checks = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["services"]["database"] = "ok"
    except Exception as e:
        checks["services"]["database"] = f"error: {str(e)}"
        checks["status"] = "unhealthy"
    
    return checks