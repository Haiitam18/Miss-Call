import asyncio
from db import init_db
import models

async def run():
    await init_db()
    print("Tables créées !")

if __name__ == "__main__":
    asyncio.run(run())