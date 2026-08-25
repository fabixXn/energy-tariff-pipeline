import pandas as pd

from extract import extract_data
from transform import transform_data


MONTHS = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}


def prepare_model_data(df):

    df = df.copy()

    # Convertir el nombre del mes a número
    df["mes"] = df["periodo"].map(MONTHS)

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