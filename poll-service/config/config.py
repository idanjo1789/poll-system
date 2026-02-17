from pydantic import BaseSettings


class Settings(BaseSettings):
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DATABASE: str = "poll_db"
    MYSQL_HOST: str = "mysql-poll"
    MYSQL_PORT: int = 3306

    USER_SERVICE_BASE_URL: str = "http://user-service:8001"
    INTERNAL_API_KEY: str = "super-secret-key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )


settings = Settings()
