from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Study Planner API"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    bing_api_key: str = ""  # 可选，空则跳过搜索

    otp_expire_minutes: int = 10
    otp_debug_return_code: bool = True
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    admin_phones: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def admin_phone_list(self) -> List[str]:
        return [x.strip() for x in self.admin_phones.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
