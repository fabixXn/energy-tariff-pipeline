import pandas as pd

from sqlalchemy import create_engine
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingRegressor

from prepare_model import prepare_model_data


DATABASE_URL = (
    "postgresql+psycopg2://energy_user:energy_pass@localhost:5432/energy_db"
)


def generate_predictions(clean_df):

    df = prepare_model_data(clean_df)

    numeric_features = [
        "cu_total",
        "cu_lag_1",
        "cu_lag_2",
        "cu_lag_3",
        "mes",
    ]

    categorical_features = [
        "operador_de_red",
        "nivel",
    ]

    features = numeric_features + categorical_features

    # Datos para entrenar
    train_df = df.dropna(
        subset=[
            "cu_lag_1",
            "cu_lag_2",
            "cu_lag_3",
            "target_cu_next_month",
        ]
    ).copy()

    # Último registro disponible de cada operador + nivel
    prediction_df = (
        df.sort_values("fecha")
        .groupby(["operador_de_red", "nivel"])
        .tail(1)
        .copy()
    )

    prediction_df = prediction_df.dropna(
        subset=[
            "cu_lag_1",
            "cu_lag_2",
            "cu_lag_3",
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                ),
                categorical_features,
            )
        ],
        remainder="passthrough",
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                GradientBoostingRegressor(
                    random_state=42
                ),
            ),
        ]
    )

    # Entrenar
    model.fit(
        train_df[features],
        train_df["target_cu_next_month"]
    )

    # Predecir
    prediction_df["predicted_cu"] = model.predict(
        prediction_df[features]
    )

    prediction_df["target_period"] = (
        prediction_df["fecha"]
        + pd.DateOffset(months=1)
    )

    results = prediction_df[
        [
            "operador_de_red",
            "nivel",
            "fecha",
            "cu_total",
            "target_period",
            "predicted_cu",
        ]
    ].copy()

    results = results.rename(
        columns={
            "fecha": "last_observed_period",
            "cu_total": "last_cu",
        }
    )

    # Guardar predicciones
    engine = create_engine(DATABASE_URL)

    results.to_sql(
        name="tariff_predictions",
        con=engine,
        if_exists="replace",
        index=False,
    )

    return results