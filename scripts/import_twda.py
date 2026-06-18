import asyncio

from app.services.twda_import.runner import run_import


async def run() -> None:
    print("Début de l'importation des tournois")
    print("-------------------------------------")
    result = await run_import()
    print("-------------------------------------")
    print(str(result))


if __name__ == "__main__":
    asyncio.run(run())
