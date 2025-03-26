from motor.motor_asyncio import AsyncIOMotorClient
from src.core.config import settings
from loguru import logger
# Initialize logger for this module

class Database:
    client: AsyncIOMotorClient = None

    def __init__(self):
        # Get MongoDB connection string from environment variable
        self.uri = settings.MONGO_CONN_STR
        if not self.uri:
            raise ValueError("MONGO_CONN_STR environment variable is not set")
        # Remove quotes from connection string if present
        self.uri = self.uri.strip('"')
        self.name = settings.DATABASE_NAME
        self.client_options = {
            'maxPoolSize': 100,
            'minPoolSize': 10,
            'maxIdleTimeMS': 50000,
        }
        logger.debug(f"Initializing MongoDB connection with database: {self.name}")
        self.client = AsyncIOMotorClient(self.uri, **self.client_options)
        logger.info("MongoDB client initialized successfully")

    def connect_db(self):
        if not self.client:
            logger.debug("Reconnecting to MongoDB")
            self.client = AsyncIOMotorClient(self.uri, **self.client_options)
            logger.info("MongoDB client reconnected successfully")

    async def close_db(self):
        if self.client:
            logger.debug("Closing MongoDB connection")
            self.client.close()
            logger.info("MongoDB connection closed")

    @property
    def db(self):
        logger.debug(f"Accessing database: {self.name}")
        return self.client[self.name]

db = Database()

async def main():
    """Test the database configuration"""
    try:
        logger.debug(f"Database URI: {db.uri}")
        logger.debug(f"Database name: {db.name}")
        db.connect_db()
        await db.close_db()
        logger.info("Database test successful")
        print("Database test successful")
        return True
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        print(f"Database test failed: {str(e)}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())