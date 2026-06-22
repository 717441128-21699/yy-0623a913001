from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "牙科订单协同服务"
    DATABASE_URL: str = "sqlite:///./dental_order.db"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
