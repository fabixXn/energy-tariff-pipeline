import time
import uuid
from datetime import datetime, timezone

from prefect import flow, task, get_run_logger

from extract import extract_data
from transform import transform_data
from validate import validate_data
from load import load_data
from monitoring import save_pipeline_run
from predict import generate_predictions


@task(name="Extract", retries=3, retry_delay_seconds=10)
def extract_task():
    logger = get_run_logger()

    logger.info("Iniciando extracción desde Datos Abiertos Colombia")

    df = extract_data()

    logger.info(f"Extracción completada: {len(df)} registros")

    return df


@task(name="Transform")
def transform_task(df):
    logger = get_run_logger()

    logger.info("Iniciando transformación")

    clean_df = transform_data(df)

    logger.info("Transformación completada")

    return clean_df


@task(name="Validate")
def validate_task(df):
    logger = get_run_logger()

    logger.info("Iniciando validación")

    validate_data(df)

    logger.info(
        f"Validación completada: {len(df)} registros"
    )

    return df


@task(name="Load")
def load_task(df):
    logger = get_run_logger()

    logger.info("Iniciando carga a PostgreSQL")

    load_data(df)

    logger.info(
        f"Carga completada: {len(df)} registros"
    )

    return df


@task(name="Predict")
def predict_task(df):
    logger = get_run_logger()

    logger.info("Iniciando modelo predictivo")

    predictions = generate_predictions(df)

    logger.info(
        f"Predicción completada: {len(predictions)} resultados"
    )

    return predictions


@flow(name="Energy Tariff ETL")
def energy_tariff_flow():

    run_id = str(uuid.uuid4())

    started_at = datetime.now(timezone.utc)
    start_time = time.perf_counter()

    rows_processed = 0

    try:

        # 1. EXTRACT
        raw_df = extract_task()

        rows_processed = len(raw_df)

        # 2. TRANSFORM
        clean_df = transform_task(raw_df)

        # 3. VALIDATE
        validated_df = validate_task(clean_df)

        # 4. LOAD
        loaded_df = load_task(validated_df)

        # 5. PREDICT
        predict_task(loaded_df)

        # Métricas de ejecución
        finished_at = datetime.now(timezone.utc)

        duration = time.perf_counter() - start_time

        save_pipeline_run(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            status="COMPLETED",
            duration_seconds=duration,
            rows_processed=rows_processed,
        )

    except Exception as error:

        finished_at = datetime.now(timezone.utc)

        duration = time.perf_counter() - start_time

        save_pipeline_run(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            status="FAILED",
            duration_seconds=duration,
            rows_processed=rows_processed,
            error_message=str(error),
        )

        raise


if __name__ == "__main__":
    energy_tariff_flow()