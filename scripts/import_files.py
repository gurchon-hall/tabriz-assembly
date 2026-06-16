import asyncio

from app.services.vtes_data.runner import run_import


async def run() -> None:
    print("Début de l'importation")
    print("-------------------------------------")
    counters = await run_import()
    print("-------------------------------------")
    print(str(counters))


if __name__ == "__main__":
    asyncio.run(run())
