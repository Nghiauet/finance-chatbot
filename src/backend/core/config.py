from pydantic import BaseSettings

class Settings(BaseSettings):
    s3_bucket: str
    s3_region: str
    
    class Config:
        env_file = ".env"

settings = Settings() 