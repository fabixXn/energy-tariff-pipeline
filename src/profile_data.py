from extract import extract_data


df = extract_data()

print("\n--- DIMENSIONES ---")
print("Filas:", df.shape[0])
print("Columnas:", df.shape[1])


print("\n--- TIPOS DE DATOS ---")
print(df.dtypes)


print("\n--- VALORES NULOS ---")
print(df.isnull().sum())


print("\n--- DUPLICADOS ---")
print("Filas duplicadas:", df.duplicated().sum())


print("\n--- AÑOS DISPONIBLES ---")
print(df["a_o"].unique())


print("\n--- PERIODOS DISPONIBLES ---")
print(df["periodo"].unique())


print("\n--- OPERADORES ---")
print(df["operador_de_red"].unique())


print("\n--- NIVELES ---")
print(df["nivel"].unique())
print("EL ARCHIVO SE ESTA EJECUTANDO")