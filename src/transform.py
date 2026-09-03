import pandas as pd

from extract import extract_data


NUMERIC_COLUMNS = [
    "cu_total",
    "costo_compra_gm_i",
    "cargo_transporte_stn_tm",
    "cargo_transporte_sdl_dn_m",
    "margen_comercializaci_n_cvm",
    "costo_g_t_p_rdidas_prn_m",
    "restricciones_rm",
    "cot",
    "cfm_j_fact",
]


def transform_data(df):

    df = df.copy()

    df = df.drop(
        columns=[":id", ":version", ":created_at", ":updated_at"],
        errors="ignore",
    )
    # 1. Eliminar espacios sobrantes
    df["operador_de_red"] = df["operador_de_red"].str.strip()
    df["nivel"] = df["nivel"].str.strip()
    df["periodo"] = df["periodo"].astype("string").str.strip().str.capitalize()

    # 2. Normalizar nombres de operadores
    df["operador_de_red"] = df["operador_de_red"].replace({
        "CELSIA - Valle del Cauca": "CELSIA Colombia - Valle del Cauca",
        "CELSIA - Tolima": "CELSIA Colombia - Tolima",
    })

    # 3. Normalizar nombres de niveles
    df["nivel"] = df["nivel"].replace({
        "Nivel 1 ( Propiedad OR )": "Nivel 1 (Propiedad OR)",
        "Nivel 1  (Propiedad Cliente)": "Nivel 1 (Propiedad Cliente)",
        "NIVEL II": "Nivel II",
        "NIVEL III": "Nivel III",
    })

    # 4. Convertir año a número
    df["a_o"] = pd.to_numeric(
        df["a_o"],
        errors="coerce"
    )

    # 5. Convertir columnas de tarifas y costos a números
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df


if __name__ == "__main__":

    raw_df = extract_data()

    clean_df = transform_data(raw_df)

    print("\n--- TIPOS DESPUÉS DE TRANSFORMAR ---")
    print(clean_df.dtypes)

    print("\n--- OPERADORES NORMALIZADOS ---")
    print(clean_df["operador_de_red"].unique())

    print("\n--- NIVELES NORMALIZADOS ---")
    print(clean_df["nivel"].unique())

    print("\n--- NULOS DESPUÉS DE TRANSFORMAR ---")
    print(clean_df.isnull().sum())

    clean_df.head(10).to_csv("data/preview.csv", index=False)
