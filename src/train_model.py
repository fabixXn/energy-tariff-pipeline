import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    mean_absolute_percentage_error
)

from extract import extract_data
from transform import transform_data
from prepare_model import prepare_model_data


# 1. Obtener y preparar datos
raw_df = extract_data()
clean_df = transform_data(raw_df)
df = prepare_model_data(clean_df)


# 2. Quitar filas que todavía no tienen suficiente histórico
model_df = df.dropna(
    subset=[
        "cu_lag_1",
        "cu_lag_2",
        "cu_lag_3",
        "target_cu_next_month"
    ]
).copy()


# 3. Variables que utilizará el modelo
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

X = model_df[features]
y = model_df["target_cu_next_month"]


# 4. Separación temporal:
# últimos 3 meses para prueba
dates = sorted(model_df["fecha"].unique())

test_dates = dates[-3:]

train_mask = ~model_df["fecha"].isin(test_dates)
test_mask = model_df["fecha"].isin(test_dates)

X_train = X[train_mask]
X_test = X[test_mask]

y_train = y[train_mask]
y_test = y[test_mask]


# 5. Preparar variables categóricas
preprocessor = ColumnTransformer(
    transformers=[
        ("categorical", OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False
        ), categorical_features),
    ],
    remainder="passthrough"
)


# 6. Modelo
model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", GradientBoostingRegressor(
            random_state=42
        ))
    ]
)


# 7. Entrenar
model.fit(X_train, y_train)


# 8. Predecir sobre datos de prueba
predictions = model.predict(X_test)


# 9. Evaluar
mae = mean_absolute_error(y_test, predictions)

rmse = np.sqrt(
    mean_squared_error(y_test, predictions)

)
mape = mean_absolute_percentage_error(
    y_test,
    predictions
) * 100

# 10. Baseline:
# asumir que el próximo mes será igual al actual
baseline_predictions = X_test["cu_total"]

baseline_mae = mean_absolute_error(
    y_test,
    baseline_predictions
)


print("\n--- RESULTADOS DEL MODELO ---")
print(f"Registros entrenamiento: {len(X_train)}")
print(f"Registros prueba: {len(X_test)}")

print(f"\nMAE Gradient Boosting: {mae:.2f}")
print(f"RMSE Gradient Boosting: {rmse:.2f}")
print(f"MAPE Gradient Boosting: {mape:.2f}%")

print(f"\nMAE Baseline: {baseline_mae:.2f}")

