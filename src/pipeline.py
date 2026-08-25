from extract import extract_data
from transform import transform_data
from validate import validate_data
from load import load_data


def run_pipeline():

    print("Iniciando pipeline...")

    # 1. Extraer
    raw_df = extract_data()
    print(f"Extracción completada: {len(raw_df)} registros")

    # 2. Transformar
    clean_df = transform_data(raw_df)
    print("Transformación completada")

    # 3. Validar
    validate_data(clean_df)

    # 4. Cargar
    load_data(clean_df)

    print("Pipeline finalizado correctamente")


if __name__ == "__main__":
    run_pipeline()