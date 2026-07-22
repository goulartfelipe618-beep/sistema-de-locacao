"""Atalho: python -m scripts.seed_demo_data"""

from scripts.demo_data.seed import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
