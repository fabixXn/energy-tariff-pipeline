from sqlalchemy import create_engine
import pandas as pd
from config import get_database_url


def save_pipeline_run(
    run_id,
    started_at,
    finished_at,
    status,
    duration_seconds,
    rows_processed,
    error_message=None
):

    engine = create_engine(get_database_url())

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
