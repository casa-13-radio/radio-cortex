# api/routes/tracks.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_session
from models.track import Track

router = APIRouter()

@router.get("/tracks")
async def list_tracks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Track))
    tracks = result.scalars().all()
    return tracks