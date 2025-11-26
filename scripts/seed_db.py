"""
Seed database with initial data (licenses).

Usage:
    python scripts/seed_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from models.database import AsyncSessionLocal
from models.license import License


async def seed_licenses(session):
    """Seed Creative Commons licenses"""
    print("\n📜 Seeding licenses...")
    
    licenses_data = [
        {
            "short_code": "CC0",
            "full_name": "CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
            "url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "allows_commercial": True,
            "allows_derivatives": True,
            "requires_attribution": False,
            "requires_share_alike": False,
            "description": "The person has waived all copyright and related rights to the work",
            "icon_url": "https://licensebuttons.net/p/zero/1.0/88x31.png",
        },
        {
            "short_code": "CC-BY",
            "full_name": "Attribution 4.0 International (CC BY 4.0)",
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "allows_commercial": True,
            "allows_derivatives": True,
            "requires_attribution": True,
            "requires_share_alike": False,
            "description": "You must give appropriate credit, provide a link to the license, and indicate if changes were made",
            "icon_url": "https://licensebuttons.net/l/by/4.0/88x31.png",
        },
        {
            "short_code": "CC-BY-SA",
            "full_name": "Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "allows_commercial": True,
            "allows_derivatives": True,
            "requires_attribution": True,
            "requires_share_alike": True,
            "description": "You must give credit and distribute your contributions under the same license as the original",
            "icon_url": "https://licensebuttons.net/l/by-sa/4.0/88x31.png",
        },
        {
            "short_code": "CC-BY-NC",
            "full_name": "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)",
            "url": "https://creativecommons.org/licenses/by-nc/4.0/",
            "allows_commercial": False,
            "allows_derivatives": True,
            "requires_attribution": True,
            "requires_share_alike": False,
            "description": "You must give credit. NonCommercial use only",
            "icon_url": "https://licensebuttons.net/l/by-nc/4.0/88x31.png",
        },
        {
            "short_code": "CC-BY-NC-SA",
            "full_name": "Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)",
            "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "allows_commercial": False,
            "allows_derivatives": True,
            "requires_attribution": True,
            "requires_share_alike": True,
            "description": "You must give credit, use for NonCommercial purposes, and distribute under same license",
            "icon_url": "https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png",
        },
        {
            "short_code": "Public Domain",
            "full_name": "Public Domain (Pre-1924 or expired copyright)",
            "url": "https://en.wikipedia.org/wiki/Public_domain",
            "allows_commercial": True,
            "allows_derivatives": True,
            "requires_attribution": False,
            "requires_share_alike": False,
            "description": "No copyright restrictions apply. Work is in the public domain",
            "icon_url": None,
        },
    ]
    
    created = 0
    skipped = 0
    
    for license_data in licenses_data:
        # Check if license already exists
        stmt = select(License).where(License.short_code == license_data["short_code"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if not existing:
            license = License(**license_data)
            session.add(license)
            created += 1
            print(f"  ✅ Created license: {license_data['short_code']}")
        else:
            skipped += 1
            print(f"  ℹ️  License already exists: {license_data['short_code']}")
    
    if created > 0:
        await session.commit()
        print(f"\n✅ Successfully created {created} licenses")
    
    if skipped > 0:
        print(f"ℹ️  Skipped {skipped} existing licenses")
    
    return created


async def verify_database():
    """Verify database state after seeding"""
    print("\n🔍 Verifying database...")
    
    async with AsyncSessionLocal() as session:
        from models.track import Track
        from models.artist import Artist
        
        # Count licenses
        license_count = await session.scalar(select(func.count()).select_from(License))
        print(f"  📜 Licenses: {license_count}")
        
        # Count artists
        artist_count = await session.scalar(select(func.count()).select_from(Artist))
        print(f"  👤 Artists: {artist_count}")
        
        # Count tracks
        track_count = await session.scalar(select(func.count()).select_from(Track))
        print(f"  🎵 Tracks: {track_count}")
        
        # Show license details
        stmt = select(License).order_by(License.short_code)
        result = await session.execute(stmt)
        licenses = result.scalars().all()
        
        if licenses:
            print("\n📋 Available Licenses:")
            for lic in licenses:
                commercial = "✅" if lic.allows_commercial else "❌"
                derivatives = "✅" if lic.allows_derivatives else "❌"
                print(f"  • {lic.short_code:15} - Commercial: {commercial}  Derivatives: {derivatives}")


async def main():
    """Main seeding function"""
    print("\n" + "="*70)
    print("🌱 RADIO CORTEX - DATABASE SEEDING")
    print("="*70)
    
    try:
        async with AsyncSessionLocal() as session:
            # Seed licenses
            created_licenses = await seed_licenses(session)
        
        # Import here to avoid circular import
        from sqlalchemy import func
        
        # Verify
        await verify_database()
        
        print("\n" + "="*70)
        print("✅ Database seeding completed successfully!")
        print("="*70 + "\n")
        
        if created_licenses == 0:
            print("💡 Tip: Database was already seeded. To reset:")
            print("   1. Drop database: docker-compose down -v")
            print("   2. Recreate: docker-compose up -d postgres")
            print("   3. Run migrations: alembic upgrade head")
            print("   4. Seed again: python scripts/seed_db.py\n")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())