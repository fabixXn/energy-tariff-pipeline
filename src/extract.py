import requests
import pandas as pd

API_URL = "https://www.datos.gov.co/api/v3/views/ytme-6qnu/query.json"


def extract_data():
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    data = response.json()
    df = pd.DataFrame(data)

    return df


if __name__ == "__main__":
    df = extract_data()

    print(df.head())
    print("\nFilas:", len(df))
    print("\nColumnas:")
    print(df.columns.tolist())