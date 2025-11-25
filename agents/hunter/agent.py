"""
The Hunter Agent - Autonomous CC Music Collector
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser
import httpx
import yt_dlp
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from models.artist import Artist
from models.license import License
from models.track import Track

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class TrackMetadata(BaseModel):
    """Metadata extracted from source"""
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    duration_seconds: Optional[int] = None
    license: str
    license_url: Optional[HttpUrl] = None
    source_url: HttpUrl
    audio_url: HttpUrl
    file_size_bytes: Optional[int] = None
    format: str = "mp3"
    id3_tags: Dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    collected_by: str = "hunter_agent_v1"
    
    def generate_hash(self) -> str:
        content = f"{self.title}|{self.artist}|{self.audio_url}"
        return hashlib.sha256(content.encode()).hexdigest()


# =============================================================================
# HUNTER AGENT
# =============================================================================

class HunterAgent:
    """The Hunter - Autonomous collector of CC-licensed music"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logging.getLogger("hunter_agent")
        self.download_dir = settings.hunter_download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = httpx.AsyncClient(timeout=settings.hunter_timeout_seconds)
        self.download_semaphore = asyncio.Semaphore(
            settings.hunter_max_concurrent_downloads
        )
        
        self.yt_dlp_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.download_dir / '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        self.allowed_licenses = ["CC-BY", "CC-BY-SA", "CC0", "Public Domain"]
    
    async def collect_from_archive_org(self, max_tracks: int = 10) -> int:
        """Collect tracks from Archive.org"""
        self.logger.info("Collecting from Archive.org...")
        
        rss_url = "https://archive.org/services/collection-rss.php?collection=audio"
        
        try:
            response = await self.client.get(rss_url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            
            self.logger.info(f"Found {len(feed.entries)} entries in RSS")
            
            collected = 0
            for entry in feed.entries[:max_tracks]:
                metadata = self._extract_rss_metadata(entry)
                if metadata and self._validate_metadata(metadata):
                    success = await self.ingest_track(metadata)
                    if success:
                        collected += 1
            
            self.logger.info(f"Collected {collected}/{max_tracks} tracks from Archive.org")
            return collected
            
        except Exception as e:
            self.logger.error(f"Error collecting from Archive.org: {e}")
            return 0
    
    def _extract_rss_metadata(self, entry: Dict) -> Optional[TrackMetadata]:
        """Extract metadata from RSS entry"""
        try:
            title = entry.get('title', 'Unknown Title')
            
            # Try to parse "Artist - Title" format
            if ' - ' in title:
                artist, title = title.split(' - ', 1)
            else:
                artist = entry.get('author', None)
            
            # License detection
            license = None
            license_url = None
            
            if hasattr(entry, 'rights'):
                license = self._parse_license_string(entry.rights)
            if hasattr(entry, 'license'):
                license = self._parse_license_string(entry.license)
            
            for link in entry.get('links', []):
                if 'creativecommons.org' in link.get('href', ''):
                    license_url = link['href']
                    license = self._parse_license_from_url(license_url)
                    break
            
            if not license:
                desc = entry.get('summary', '') + entry.get('description', '')
                license = self._parse_license_string(desc)
            
            if not license:
                return None
            
            # Audio URL
            audio_url = None
            for link in entry.get('enclosures', []):
                if link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    break
            
            if not audio_url:
                audio_url = entry.get('link')
            
            if not audio_url:
                return None
            
            return TrackMetadata(
                title=title.strip(),
                artist=artist.strip() if artist else None,
                license=license,
                license_url=license_url,
                source_url=entry.get('link', audio_url),
                audio_url=audio_url,
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting RSS metadata: {e}")
            return None
    
    def _parse_license_string(self, text: str) -> Optional[str]:
        """Parse license from text string"""
        text = text.upper()
        
        patterns = {
            r'CC0|PUBLIC\s*DOMAIN\s*DEDICATION': 'CC0',
            r'CC-?BY-?SA': 'CC-BY-SA',
            r'CC-?BY': 'CC-BY',
            r'PUBLIC\s*DOMAIN': 'Public Domain',
        }
        
        for pattern, license_code in patterns.items():
            if re.search(pattern, text):
                return license_code
        
        return None
    
    def _parse_license_from_url(self, url: str) -> Optional[str]:
        """Parse license from Creative Commons URL"""
        match = re.search(r'creativecommons\.org/(?:licenses|publicdomain)/([^/]+)', url)
        if match:
            license_code = match.group(1).upper().replace('-', '-')
            return f"CC-{license_code}" if license_code != 'ZERO' else 'CC0'
        return None
    
    def _validate_metadata(self, metadata: TrackMetadata) -> bool:
        """Validate if metadata meets filtering criteria"""
        if metadata.license not in self.allowed_licenses:
            return False
        
        if metadata.duration_seconds:
            if metadata.duration_seconds < 60 or metadata.duration_seconds > 600:
                return False
        
        return True
    
    async def ingest_track(self, metadata: TrackMetadata) -> bool:
        """Ingest a track: check duplicates, download, save to DB"""
        track_hash = metadata.generate_hash()
        
        # Check duplicates by source URL
        stmt = select(Track).where(Track.source_url == str(metadata.source_url))
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            self.logger.debug(f"Track already exists: {metadata.title}")
            return False
        
        async with self.download_semaphore:
            try:
                # Download audio file
                local_path = await self.download_audio(metadata)
                if not local_path:
                    return False
                
                # Get or create artist
                artist = await self._get_or_create_artist(metadata.artist or "Unknown Artist")
                
                # Get license
                license = await self._get_license(metadata.license)
                if not license:
                    self.logger.error(f"License not found: {metadata.license}")
                    return False
                
                # Create track record
                track = Track(
                    title=metadata.title,
                    artist_id=artist.id,
                    album=metadata.album,
                    license_id=license.id,
                    audio_url=str(metadata.audio_url),
                    duration_seconds=metadata.duration_seconds or 180,
                    file_size_bytes=metadata.file_size_bytes,
                    source_url=str(metadata.source_url),
                    id3_tags=metadata.id3_tags,
                    status="pending_enrichment",
                    collected_by=metadata.collected_by,
                )
                
                self.session.add(track)
                await self.session.commit()
                
                self.logger.info(f"✅ Ingested: {metadata.title} by {metadata.artist}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to ingest {metadata.title}: {e}")
                await self.session.rollback()
                return False
    
    async def download_audio(self, metadata: TrackMetadata) -> Optional[Path]:
        """Download audio file using yt-dlp"""
        self.logger.info(f"Downloading: {metadata.audio_url}")
        
        try:
            with yt_dlp.YoutubeDL(self.yt_dlp_opts) as ydl:
                info = ydl.extract_info(str(metadata.audio_url), download=True)
                
                if info:
                    metadata.duration_seconds = info.get('duration')
                    metadata.file_size_bytes = info.get('filesize')
                    
                    filename = ydl.prepare_filename(info)
                    return Path(filename)
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None
    
    async def _get_or_create_artist(self, name: str) -> Artist:
        """Get existing artist or create new one"""
        name_normalized = name.lower().strip()
        
        stmt = select(Artist).where(Artist.name_normalized == name_normalized)
        result = await self.session.execute(stmt)
        artist = result.scalar_one_or_none()
        
        if not artist:
            artist = Artist(
                name=name,
                name_normalized=name_normalized,
            )
            self.session.add(artist)
            await self.session.flush()
        
        return artist
    
    async def _get_license(self, short_code: str) -> Optional[License]:
        """Get license by short code"""
        stmt = select(License).where(License.short_code == short_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def close(self):
        """Cleanup resources"""
        await self.client.aclose()


# =============================================================================
# CLI
# =============================================================================

async def main():
    """CLI entry point"""
    import argparse
    from models.database import AsyncSessionLocal
    
    parser = argparse.ArgumentParser(description="Hunter Agent - CC Music Collector")
    parser.add_argument('--source', default='archive.org', help='Source to collect from')
    parser.add_argument('--max-tracks', type=int, default=10, help='Maximum tracks to collect')
    parser.add_argument('--log-level', default='INFO')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async with AsyncSessionLocal() as session:
        agent = HunterAgent(session)
        
        try:
            if args.source == 'archive.org':
                collected = await agent.collect_from_archive_org(args.max_tracks)
                print(f"✅ Collected {collected} tracks")
        finally:
            await agent.close()


if __name__ == "__main__":
    asyncio.run(main())