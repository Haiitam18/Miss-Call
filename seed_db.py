import asyncio
from db import AsyncSessionLocal, init_db
from models import Artisan
from sqlalchemy import select

async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Numéros sont au format E.164 (+33...)
        twilio_number = "+33939240109" 
        notification_number = "+33783387632"
        
        stmt = select(Artisan).where(Artisan.twilio_phone_number == twilio_number)
        result = await session.execute(stmt)
        existing = result.scalars().first()
        
        if not existing:
            new_artisan = Artisan(
                nom_societe="Plomberie Marwan",
                twilio_phone_number=twilio_number,
                notification_phone_number=notification_number,
                # Horaires pour la maintenance
                business_hours={"weekdays": ["08:00", "18:00"]} 
            )
            session.add(new_artisan)
            await session.commit()
            print("✅ Artisan de test initialisé avec succès.")
        else:
            print(f"ℹ️ Artisan {twilio_number} déjà présent en base.")

if __name__ == "__main__":
    asyncio.run(seed())