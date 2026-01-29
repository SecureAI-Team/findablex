"""Crawler service main entry point."""
import asyncio
import signal
import sys
from typing import Optional

from app.config import settings
from app.orchestrator import CrawlOrchestrator


async def main():
    """Main entry point for the crawler service."""
    orchestrator = CrawlOrchestrator()
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def shutdown_handler():
        print("Shutdown signal received")
        asyncio.create_task(orchestrator.shutdown())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)
    
    try:
        print("Starting FindableX Crawler Service...")
        await orchestrator.start()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
