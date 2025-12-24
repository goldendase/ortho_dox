"""MongoDB connection manager."""

from motor.motor_asyncio import AsyncIOMotorClient

from api.config import settings


class MongoDB:
    """MongoDB connection manager."""

    client: AsyncIOMotorClient | None = None
    db_dox = None
    db_raw = None

    @classmethod
    async def connect(cls):
        """Connect to MongoDB."""
        cls.client = AsyncIOMotorClient(settings.mongodb_uri)
        cls.db_dox = cls.client[settings.db_name_dox]
        cls.db_raw = cls.client[settings.db_name_raw]

    @classmethod
    async def close(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
