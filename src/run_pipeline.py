"""Ejecutor autónomo para despliegues donde no se utiliza Prefect Server."""

import time
import uuid
from datetime import datetime, timezone

from extract import extract_data
from load import load_data
from monitoring import save_pipeline_run
from predict import generate_predictions
from transform import transform_data
from validate import validate_data


def run_pipeline() -> None:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    started_timer = time.perf_counter()
    rows_processed = 0

    try:
        print("Extrayendo tarifas...")
        raw_df = extract_data()
        rows_processed = len(raw_df)
        clean_df = transform_data(raw_df)
        validate_data(clean_df)
        load_data(clean_df)
        predictions = generate_predictions(clean_df)
        save_pipeline_run(
            run_id=run_id,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            status="COMPLETED",
            duration_seconds=time.perf_counter() - started_timer,
            rows_processed=rows_processed,
        )
        print(f"Pipeline completado: {rows_processed} tarifas, {len(predictions)} predicciones")
    except Exception as error:
        try:
            save_pipeline_run(
                run_id=run_id,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                status="FAILED",
                duration_seconds=time.perf_counter() - started_timer,
                rows_processed=rows_processed,
                error_message=str(error),
            )
        except Exception as monitoring_error:
            print(f"No se pudo registrar el fallo: {monitoring_error}")
        raise


if __name__ == "__main__":
    run_pipeline()
