from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings
import os

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
        self.client = AsyncIOMotorClient(self.uri, **self.client_options)

    def connect_db(self):
        if not self.client:
            self.client = AsyncIOMotorClient(self.uri, **self.client_options)

    async def close_db(self):
        if self.client:
            self.client.close()

    @property
    def db(self):
        return self.client[self.name]

db = Database()

async def main():
    """Test the database configuration"""
    try:
        print("[DEBUG] db.uri: ", db.uri)
        print("[DEBUG] db.name: ", db.name)
        await db.connect_db()
        await db.close_db()
        print("Database test successful")
        return True
    except Exception as e:
        print(f"Database test failed: {str(e)}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())