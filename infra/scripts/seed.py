#!/usr/bin/env python3
"""Standalone seed script for running outside of Docker."""
import asyncio
import os
import sys

# Add the api package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/api'))

from app.db.seed import seed_database

if __name__ == "__main__":
    asyncio.run(seed_database())
