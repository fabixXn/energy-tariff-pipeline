from sqlalchemy import create_engine

from extract import extract_data
from transform import transform_data


DATABASE_URL = (
    "postgresql+psycopg2://energy_user:energy_pass@localhost:5432/energy_db"
)


def load_data(df):

    engine = create_engine(DATABASE_URL)

    df.to_sql(
        name="energy_tariffs",
        con=engine,
        if_exists="replace",
        index=False
    )

    print(f"Carga exitosa: {len(df)} registros")


if __name__ == "__main__":

    raw_df = extract_data()
    clean_df = transform_data(raw_df)

    load_data(clean_df)