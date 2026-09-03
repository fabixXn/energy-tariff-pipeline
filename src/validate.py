from extract import extract_data
from transform import transform_data


def validate_data(df):

    required_columns = {"operador_de_red", "nivel", "a_o", "periodo", "cu_total"}
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(missing_columns)}")

    if df.empty:
        raise ValueError("El dataset está vacío")

    if df["cu_total"].isnull().any():
        raise ValueError("Hay valores nulos en CU Total")

    if (df["cu_total"] < 0).any():
        raise ValueError("Hay tarifas CU Total negativas")

    if df["a_o"].isnull().any():
        raise ValueError("Hay años inválidos")

    if not df["a_o"].between(2000, 2100).all():
        raise ValueError("Hay años fuera del rango permitido")

    if df[["operador_de_red", "nivel", "periodo"]].isnull().any().any():
        raise ValueError("Hay dimensiones tarifarias incompletas")

    duplicate_key = ["operador_de_red", "nivel", "a_o", "periodo"]
    if df.duplicated(duplicate_key).any():
        raise ValueError("Hay periodos duplicados para un operador y nivel")

    print("VALIDACIÓN EXITOSA")
    print("Filas validadas:", len(df))


if __name__ == "__main__":

    raw_df = extract_data()
    clean_df = transform_data(raw_df)

    validate_data(clean_df)
