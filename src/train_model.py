from extract import extract_data
from modeling import evaluate_candidates
from prepare_model import prepare_model_data
from transform import transform_data


def main() -> None:
    df = prepare_model_data(transform_data(extract_data()))
    best, evaluations = evaluate_candidates(df)
    print("\n--- COMPARACIÓN TEMPORAL DE MODELOS ---")
    print(f"Entrenamiento: {best.train_rows} | Prueba: {best.test_rows}")
    for result in sorted(evaluations, key=lambda item: item.mae):
        selected = "  <-- seleccionado" if result.model_name == best.model_name else ""
        print(
            f"{result.model_name:22} MAE={result.mae:7.2f} "
            f"RMSE={result.rmse:7.2f} MAPE={result.mape:6.2f}%{selected}"
        )


if __name__ == "__main__":
    main()
