from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://energy_user:energy_pass@localhost:5432/energy_db"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    result = connection.execute(text("SELECT 1;"))
    print("Conexión exitosa:", result.scalar())