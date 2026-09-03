import os


DEFAULT_DATABASE_URL = (
    "postgresql+psycopg2://energy_user:energy_pass@localhost:5432/energy_db"
)


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
