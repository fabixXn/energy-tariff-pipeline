from sqlalchemy import create_engine
import pandas as pd


DATABASE_URL = (
    "postgresql+psycopg2://energy_user:energy_pass@localhost:5432/energy_db"
)


def save_pipeline_run(
    run_id,
    started_at,
    finished_at,
    status,
    duration_seconds,
    rows_processed,
    error_message=None
):

    engine = create_engine(DATABASE_URL)

    data = pd.DataFrame([{
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "duration_seconds": duration_seconds,
        "rows_processed": rows_processed,
        "error_message": error_message
    }])

    data.to_sql(
        "pipeline_runs",
        con=engine,
        if_exists="append",
        index=False
    )