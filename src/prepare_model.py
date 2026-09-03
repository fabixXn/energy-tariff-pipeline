import pandas as pd

from extract import extract_data
from transform import transform_data


MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def prepare_model_data(df):

    df = df.copy()

    # Convertir el nombre del mes a número
    period = df["periodo"].astype("string").str.strip().str.lower()
    df["mes"] = pd.to_numeric(period, errors="coerce").fillna(period.map(MONTHS))
    if df["mes"].isna().any():
        invalid = sorted(period[df["mes"].isna()].dropna().unique())
        raise ValueError(f"Periodos no reconocidos: {', '.join(invalid)}")

    # Crear una fecha real
    df["fecha"] = pd.to_datetime(
        dict(
            year=df["a_o"],
            month=df["mes"],
            day=1
        )
    )

    # Ordenar cronológicamente
    df = df.sort_values(
        ["operador_de_red", "nivel", "fecha"]
    )

    group = df.groupby(
        ["operador_de_red", "nivel"]
    )

    # CU Total de meses anteriores
    df["cu_lag_1"] = group["cu_total"].shift(1)
    df["cu_lag_2"] = group["cu_total"].shift(2)
    df["cu_lag_3"] = group["cu_total"].shift(3)

    # Lo que queremos predecir:
    # CU Total del mes siguiente
    df["target_cu_next_month"] = group["cu_total"].shift(-1)

    # No tratar como consecutivos registros separados por huecos temporales.
    for lag in (1, 2, 3):
        lag_date = group["fecha"].shift(lag)
        expected = df["fecha"] - pd.DateOffset(months=lag)
        df.loc[lag_date.ne(expected), f"cu_lag_{lag}"] = pd.NA
    next_date = group["fecha"].shift(-1)
    expected_next = df["fecha"] + pd.DateOffset(months=1)
    df.loc[next_date.ne(expected_next), "target_cu_next_month"] = pd.NA

    return df


if __name__ == "__main__":

    raw_df = extract_data()
    clean_df = transform_data(raw_df)

    model_df = prepare_model_data(clean_df)

    columns = [
        "fecha",
        "operador_de_red",
        "nivel",
        "cu_total",
        "cu_lag_1",
        "cu_lag_2",
        "cu_lag_3",
        "target_cu_next_month",
    ]

    print(model_df[columns].tail(20).to_string(index=False))
