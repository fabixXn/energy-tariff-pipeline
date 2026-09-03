from sqlalchemy import create_engine, text
from config import get_database_url

engine = create_engine(get_database_url())

with engine.connect() as connection:
    result = connection.execute(text("SELECT 1;"))
    print("Conexión exitosa:", result.scalar())
