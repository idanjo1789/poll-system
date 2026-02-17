from databases import Database
from config.config import settings

database = Database(settings.DATABASE_URL)

