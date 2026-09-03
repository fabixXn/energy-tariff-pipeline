from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


NUMERIC_FEATURES = ["cu_total", "cu_lag_1", "cu_lag_2", "cu_lag_3", "mes"]
CATEGORICAL_FEATURES = ["operador_de_red", "nivel"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


@dataclass
class ModelEvaluation:
    model_name: str
    mae: float
    rmse: float
    mape: float
    baseline_mae: float
    train_rows: int
    test_rows: int


def _pipeline(estimator) -> Pipeline:
    transformer = ColumnTransformer(
        [("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES)],
        remainder="passthrough",
    )
    return Pipeline([("preprocessor", transformer), ("model", estimator)])


def candidate_models() -> dict[str, Pipeline]:
    return {
        "Ridge": _pipeline(Ridge(alpha=10.0)),
        "Extra Trees": _pipeline(ExtraTreesRegressor(
            n_estimators=400, min_samples_leaf=2, max_features=0.8,
            random_state=42, n_jobs=-1,
        )),
        "Random Forest": _pipeline(RandomForestRegressor(
            n_estimators=400, min_samples_leaf=2, max_features=0.8,
            random_state=42, n_jobs=-1,
        )),
        "Gradient Boosting": _pipeline(GradientBoostingRegressor(
            n_estimators=150, learning_rate=0.04, max_depth=2,
            loss="huber", random_state=42,
        )),
    }


def usable_rows(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    required = FEATURES + (["target_cu_next_month"] if include_target else [])
    return df.dropna(subset=required).copy()


def evaluate_candidates(df: pd.DataFrame, test_months: int = 3) -> tuple[ModelEvaluation, list[ModelEvaluation]]:
    model_df = usable_rows(df)
    dates = sorted(model_df["fecha"].unique())
    if len(dates) <= test_months:
        raise ValueError("No hay suficientes periodos para una validación temporal")
    test_dates = dates[-test_months:]
    train_df = model_df[~model_df["fecha"].isin(test_dates)]
    test_df = model_df[model_df["fecha"].isin(test_dates)]
    y_test = test_df["target_cu_next_month"]
    baseline = test_df["cu_total"]
    baseline_mae = float(mean_absolute_error(y_test, baseline))
    evaluations = [ModelEvaluation(
        "Baseline persistente", baseline_mae,
        float(np.sqrt(mean_squared_error(y_test, baseline))),
        float(mean_absolute_percentage_error(y_test, baseline) * 100),
        baseline_mae, len(train_df), len(test_df),
    )]
    for name, model in candidate_models().items():
        model.fit(train_df[FEATURES], train_df["target_cu_next_month"])
        predicted = model.predict(test_df[FEATURES])
        evaluations.append(ModelEvaluation(
            name, float(mean_absolute_error(y_test, predicted)),
            float(np.sqrt(mean_squared_error(y_test, predicted))),
            float(mean_absolute_percentage_error(y_test, predicted) * 100),
            baseline_mae, len(train_df), len(test_df),
        ))
    return min(evaluations, key=lambda item: item.mae), evaluations


def fit_model(df: pd.DataFrame, model_name: str) -> Pipeline | None:
    if model_name == "Baseline persistente":
        return None
    model = candidate_models()[model_name]
    train_df = usable_rows(df)
    model.fit(train_df[FEATURES], train_df["target_cu_next_month"])
    return model
