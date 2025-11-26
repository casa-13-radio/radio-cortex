"""
The Librarian Agent - Metadata Enrichment with LLM
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from groq import AsyncGroq
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from models.track import Track

logger = logging.getLogger(__name__)


# =============================================================================
# LIBRARIAN AGENT
# =============================================================================

class LibrarianAgent:
    """The Librarian - Enriches track metadata using AI"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logging.getLogger("librarian_agent")
        
        # LLM Client
        if settings.groq_api_key:
            self.llm_client = AsyncGroq(api_key=settings.groq_api_key)
        else:
            self.logger.warning("GROQ_API_KEY not set, using dummy classification")
            self.llm_client = None
        
        # Embedding Model (loaded locally)
        self.logger.info(f"Loading embedding model: {settings.librarian_embedding_model}")
        self.embedding_model = SentenceTransformer(settings.librarian_embedding_model)
        self.logger.info("Embedding model loaded")
    
    async def process_pending_tracks(self, max_tracks: int = 10) -> int:
        """Process tracks in pending_enrichment status"""
        self.logger.info(f"Processing up to {max_tracks} pending tracks...")
        
        stmt = (
            select(Track)
            .where(Track.status == "pending_enrichment")
            .limit(max_tracks)
        )
        result = await self.session.execute(stmt)
        tracks = result.scalars().all()
        
        self.logger.info(f"Found {len(tracks)} tracks to process")
        
        processed = 0
        for track in tracks:
            try:
                await self.enrich_track(track)
                processed += 1
            except Exception as e:
                self.logger.error(f"Error processing track {track.id}: {e}")
        
        self.logger.info(f"Processed {processed}/{len(tracks)} tracks")
        return processed
    
    async def enrich_track(self, track: Track) -> None:
        """Enrich a single track with AI"""
        self.logger.info(f"Enriching: {track.title}")
        
        # Step 1: LLM Classification
        if self.llm_client:
            classification = await self._classify_with_llm(track)
        else:
            classification = self._classify_dummy(track)
        
        # Step 2: Generate Embeddings
        embedding = self._generate_embedding(track, classification)
        
        # Step 3: Update track
        track.primary_genre = classification.get("primary_genre")
        track.secondary_genres = classification.get("secondary_genres", [])
        track.mood_tags = classification.get("mood_tags", [])
        track.cultural_context = classification.get("cultural_context")
        track.embedding = embedding
        track.status = "pending_compliance"  # Next stage
        
        # Step 4: Save embedding in TrackEmbedding table
        from models.track_embedding import TrackEmbedding
        track_embedding = TrackEmbedding(
            track_id=track.id,
            embedding=embedding,
            model_version=settings.librarian_embedding_model
        )
        self.session.add(track_embedding)
        
        await self.session.commit()
        self.logger.info(f"✅ Enriched: {track.title} - Genre: {track.primary_genre}")
    
    async def _classify_with_llm(self, track: Track) -> Dict[str, Any]:
        """Classify track using LLM"""
        prompt = self._build_classification_prompt(track)
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=settings.librarian_llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a music classification expert. Analyze tracks and return JSON with genre, mood, and cultural context."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content
            
            # Clean response (remove markdown code blocks if present)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            return result
            
        except Exception as e:
            self.logger.error(f"LLM classification failed: {e}")
            return self._classify_dummy(track)
    
    def _classify_dummy(self, track: Track) -> Dict[str, Any]:
        """Fallback classification without LLM"""
        title_lower = track.title.lower()
        
        # Simple keyword-based classification
        if any(word in title_lower for word in ['jazz', 'bossa', 'swing']):
            genre = "Jazz"
        elif any(word in title_lower for word in ['rock', 'metal', 'punk']):
            genre = "Rock"
        elif any(word in title_lower for word in ['classical', 'symphony', 'concerto']):
            genre = "Classical"
        elif any(word in title_lower for word in ['electronic', 'techno', 'house']):
            genre = "Electronic"
        else:
            genre = "Unknown"
        
        return {
            "primary_genre": genre,
            "secondary_genres": [],
            "mood_tags": ["neutral"],
            "cultural_context": None,
        }
    
    def _build_classification_prompt(self, track: Track) -> str:
        """Build LLM prompt for classification"""
        return f"""Analyze this music track and classify it.

Title: {track.title}
Artist: {track.artist.name if track.artist else "Unknown"}
Album: {track.album or "Unknown"}
Duration: {track.duration_seconds}s

Return a JSON object with:
- primary_genre: Main genre (e.g., "Bossa Nova", "Jazz", "Rock")
- secondary_genres: List of 1-2 related genres
- mood_tags: List of 2-3 mood keywords (e.g., "calm", "energetic", "melancholic")
- cultural_context: Brief cultural/geographic context if identifiable (max 50 words)

Example response:
{{
  "primary_genre": "Bossa Nova",
  "secondary_genres": ["MPB", "Jazz"],
  "mood_tags": ["calm", "romantic", "sophisticated"],
  "cultural_context": "Brazilian music from the 1960s bossa nova movement"
}}

Return ONLY the JSON object, no other text."""
    
    def _generate_embedding(self, track: Track, classification: Dict[str, Any]) -> list[float]:
        """Generate semantic embedding for track"""
        # Combine all text for embedding
        text_parts = [
            track.title,
            track.artist.name if track.artist else "Unknown",
            track.album or "",
            classification.get("primary_genre", ""),
            " ".join(classification.get("secondary_genres", [])),
            " ".join(classification.get("mood_tags", [])),
            classification.get("cultural_context", ""),
        ]
        
        text = " ".join(filter(None, text_parts))
        
        # Generate embedding
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# =============================================================================
# CLI
# =============================================================================

async def main():
    """CLI entry point"""
    import argparse
    from models.database import AsyncSessionLocal
    
    parser = argparse.ArgumentParser(description="Librarian Agent - Track Enrichment")
    parser.add_argument('--max-tracks', type=int, default=10, help='Maximum tracks to process')
    parser.add_argument('--log-level', default='INFO')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async with AsyncSessionLocal() as session:
        agent = LibrarianAgent(session)
        processed = await agent.process_pending_tracks(args.max_tracks)
        print(f"✅ Processed {processed} tracks")


if __name__ == "__main__":
    asyncio.run(main())