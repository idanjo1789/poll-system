
import os
from dotenv import load_dotenv


if os.getenv("RUNNING_IN_DOCKER", "0") != "1":
    load_dotenv(override=True)

SERVICE_NAME = os.getenv("SERVICE_NAME", "user-service")

DB_USER = os.getenv("MYSQL_USER") or os.getenv("DB_USER") or "root"
DB_PASSWORD = os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD") or "root"
DB_NAME = os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME") or "user_db"
DB_HOST = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST") or "mysql-user"
DB_PORT = int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or "3306")

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

POLL_SERVICE_BASE_URL = os.getenv("POLL_SERVICE_BASE_URL", "http://poll-service:8002")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

