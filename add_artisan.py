import argparse
import asyncio
import sys

from sqlalchemy import select

from db import AsyncSessionLocal, init_db
from models import Artisan


async def add_artisan(nom: str, twilio: str, notif: str) -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        stmt = select(Artisan).where(Artisan.twilio_phone_number == twilio)
        result = await session.execute(stmt)
        existing = result.scalars().first()

        if existing:
            print(
                f"ℹ️ Artisan déjà présent pour le numéro Twilio {twilio} "
                f"({existing.nom_societe}). Aucune création."
            )
            return

        new_artisan = Artisan(
            nom_societe=nom,
            twilio_phone_number=twilio,
            notification_phone_number=notif,
        )
        session.add(new_artisan)
        await session.commit()
        print(
            f"✅ Artisan « {nom} » créé avec succès "
            f"(Twilio: {twilio}, notification: {notif})."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ajoute un artisan en base de données."
    )
    parser.add_argument("--nom", required=True, help="Nom de la société (nom_societe)")
    parser.add_argument(
        "--twilio",
        required=True,
        help="Numéro Twilio de l'artisan (twilio_phone_number)",
    )
    parser.add_argument(
        "--notif",
        required=True,
        help="Numéro de notification (notification_phone_number)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(add_artisan(args.nom, args.twilio, args.notif))
    except Exception as exc:
        print(f"❌ Impossible d'ajouter l'artisan : {exc}", file=sys.stderr)
        sys.exit(1)
