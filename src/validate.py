from extract import extract_data
from transform import transform_data


def validate_data(df):

    if df.empty:
        raise ValueError("El dataset está vacío")

    if df["cu_total"].isnull().any():
        raise ValueError("Hay valores nulos en CU Total")

    if (df["cu_total"] < 0).any():
        raise ValueError("Hay tarifas CU Total negativas")

    if df["a_o"].isnull().any():
        raise ValueError("Hay años inválidos")

    print("VALIDACIÓN EXITOSA")
    print("Filas validadas:", len(df))


if __name__ == "__main__":

    raw_df = extract_data()
    clean_df = transform_data(raw_df)

    validate_data(clean_df)