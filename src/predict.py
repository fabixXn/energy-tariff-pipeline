from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine

from config import get_database_url
from modeling import FEATURES, evaluate_candidates, fit_model, usable_rows
from prepare_model import prepare_model_data


def generate_predictions(clean_df: pd.DataFrame) -> pd.DataFrame:
    df = prepare_model_data(clean_df)
    best, _ = evaluate_candidates(df)
    model = fit_model(df, best.model_name)
    prediction_df = (
        df.sort_values("fecha")
        .groupby(["operador_de_red", "nivel"], as_index=False)
        .tail(1)
    )
    prediction_df = usable_rows(prediction_df, include_target=False)
    if prediction_df.empty:
        raise ValueError("No hay series con histórico suficiente para predecir")
    prediction_df["predicted_cu"] = (
        prediction_df["cu_total"] if model is None
        else model.predict(prediction_df[FEATURES])
    )
    prediction_df["target_period"] = prediction_df["fecha"] + pd.DateOffset(months=1)
    prediction_df["model_name"] = best.model_name
    prediction_df["validation_mae"] = best.mae
    prediction_df["baseline_mae"] = best.baseline_mae
    prediction_df["generated_at"] = datetime.now(timezone.utc)
    results = prediction_df[[
        "operador_de_red", "nivel", "fecha", "cu_total", "target_period",
        "predicted_cu", "model_name", "validation_mae", "baseline_mae", "generated_at",
    ]].rename(columns={"fecha": "last_observed_period", "cu_total": "last_cu"})
    results.to_sql(
        "tariff_predictions", con=create_engine(get_database_url()),
        if_exists="replace", index=False,
    )
    return results
