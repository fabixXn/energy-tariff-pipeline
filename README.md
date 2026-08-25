# Energy Tariff Pipeline

Pipeline de datos para extraer tarifas de energía de **Datos Abiertos Colombia**, limpiarlas y validarlas, almacenarlas en PostgreSQL, generar una predicción mensual del costo unitario (CU) y visualizar tanto la operación como los resultados en un dashboard ejecutivo.

El proyecto demuestra un flujo de datos de extremo a extremo: **ingesta → calidad → persistencia → machine learning → monitoreo → visualización**.

## Objetivo

Construir una solución que permita:

- Consumir automáticamente información pública de tarifas de energía.
- Normalizar operadores, niveles de tensión, periodos y variables numéricas.
- Evitar la carga de datos vacíos, inválidos o con tarifas negativas.
- Persistir un histórico limpio en PostgreSQL.
- Predecir el CU del mes siguiente para cada combinación de operador y nivel.
- Registrar el resultado, duración, volumen y errores de cada ejecución.
- Presentar indicadores operativos y analíticos en Streamlit.

## Arquitectura

```mermaid
flowchart LR
    A[Datos Abiertos Colombia] -->|API HTTP| B[Extracción]
    B --> C[Transformación]
    C --> D[Validación]
    D --> E[(PostgreSQL)]
    D --> F[Preparación de variables]
    F --> G[Gradient Boosting]
    G --> E
    H[Prefect] -. orquesta y registra .-> B
    H -. métricas de ejecución .-> E
    E --> I[Dashboard Streamlit]
```

### Tecnologías

| Capa | Tecnología | Uso |
|---|---|---|
| Extracción y transformación | Python, pandas, requests | Consumo de API y preparación de datos |
| Orquestación | Prefect | Tareas, logging y reintentos |
| Persistencia | PostgreSQL, SQLAlchemy | Histórico, predicciones y monitoreo |
| Machine learning | scikit-learn | Pipeline de preprocesamiento y regresión |
| Visualización | Streamlit, Plotly | Dashboard ejecutivo e interactivo |
| Infraestructura local | Docker Compose | Base de datos reproducible |

## Flujo de ejecución

El flujo principal está definido en `src/prefect_flow.py` y ejecuta cinco etapas en orden.

### 1. Extracción

`src/extract.py` consulta el dataset público mediante HTTP y convierte la respuesta JSON en un `DataFrame`.

- Fuente: Datos Abiertos Colombia.
- Timeout de la solicitud: 30 segundos.
- `raise_for_status()` detiene el proceso ante una respuesta HTTP fallida.
- La tarea de Prefect tiene hasta **3 reintentos**, separados por 10 segundos.

### 2. Transformación

`src/transform.py` prepara los registros antes de cargarlos:

- Elimina metadatos técnicos de la fuente (`:id`, `:version`, `:created_at`, `:updated_at`).
- Quita espacios sobrantes en operador, nivel y periodo.
- Unifica variantes conocidas de nombres de operadores.
- Normaliza variantes de niveles de tensión.
- Convierte `a_o` y las columnas económicas a tipos numéricos.
- Convierte valores no interpretables a nulos mediante `errors="coerce"`.

La columna se llama `a_o` porque así llega normalizada desde la fuente original (corresponde al año).

### 3. Validación

`src/validate.py` aplica reglas que detienen el pipeline si:

- El dataset está vacío.
- Existen valores nulos en `cu_total`.
- Existen tarifas negativas.
- Existen años inválidos.

Una excepción evita que datos que incumplen estas condiciones continúen hacia PostgreSQL o el modelo.

### 4. Carga

`src/load.py` persiste el dataset limpio en `energy_tariffs` mediante SQLAlchemy y pandas.

La carga utiliza `if_exists="replace"`: cada ejecución mantiene en la tabla una fotografía completa y actualizada del dataset fuente, en lugar de anexar duplicados.

### 5. Predicción

`src/prepare_model.py` construye una fecha real combinando `a_o` y `periodo`, ordena cada serie cronológicamente y crea variables rezagadas:

- `cu_lag_1`: CU del mes anterior.
- `cu_lag_2`: CU de hace dos meses.
- `cu_lag_3`: CU de hace tres meses.
- `target_cu_next_month`: CU que se desea predecir para el mes siguiente.

`src/predict.py` entrena un `GradientBoostingRegressor` usando:

- Variables numéricas: CU actual, tres rezagos y mes.
- Variables categóricas: operador de red y nivel.
- `OneHotEncoder(handle_unknown="ignore")` para transformar las categorías.
- `random_state=42` para obtener resultados reproducibles.

Después selecciona el último registro de cada combinación **operador + nivel**, estima su CU del mes siguiente y reemplaza la tabla `tariff_predictions` con los resultados más recientes.

## Evaluación del modelo

`src/train_model.py` contiene el ejercicio de evaluación, separado del flujo productivo.

La separación es temporal: los últimos tres meses se reservan para prueba y los periodos anteriores se usan para entrenamiento. Esto evita mezclar aleatoriamente observaciones futuras con datos pasados.

Las métricas calculadas son:

- **MAE:** error absoluto promedio en unidades de CU.
- **RMSE:** penaliza con mayor intensidad los errores grandes.
- **MAPE:** error porcentual promedio.
- **Baseline MAE:** compara el modelo contra la regla sencilla de asumir que el próximo CU será igual al actual.

Para ejecutar la evaluación:

```powershell
cd src
python train_model.py
```

## Tolerancia a fallos y monitoreo

Prefect aporta observabilidad por tarea y reintenta la extracción, que es la etapa más expuesta a fallos transitorios de red.

Cada ejecución recibe un UUID y se mide con `time.perf_counter()`. Al finalizar, `src/monitoring.py` agrega una fila a `pipeline_runs` con:

- Identificador de ejecución.
- Fecha y hora de inicio y finalización en UTC.
- Estado `COMPLETED` o `FAILED`.
- Duración total en segundos.
- Cantidad de registros procesados.
- Mensaje de error, cuando aplica.

El bloque `try/except` del flujo registra también las ejecuciones fallidas y luego vuelve a lanzar la excepción para conservar el comportamiento correcto de Prefect.

> **Alcance actual:** el flujo está preparado para ejecución desatendida, pero este repositorio no incluye todavía un deployment o schedule de Prefect. En producción, el siguiente paso sería desplegar `energy_tariff_flow` y asignarle una programación periódica.

## Modelo de datos

### `energy_tariffs`

Contiene la fotografía limpia del dataset fuente. Entre sus columnas relevantes están:

| Columna | Descripción |
|---|---|
| `operador_de_red` | Empresa u operador responsable de la red |
| `nivel` | Nivel de tensión o categoría tarifaria |
| `a_o` | Año del registro |
| `periodo` | Mes del registro |
| `cu_total` | Costo unitario total observado |
| Columnas de costos | Componentes de compra, transporte, comercialización y restricciones |

### `tariff_predictions`

| Columna | Descripción |
|---|---|
| `operador_de_red` | Operador de la serie predicha |
| `nivel` | Nivel de la serie predicha |
| `last_observed_period` | Último mes disponible |
| `last_cu` | CU observado en ese mes |
| `target_period` | Mes para el cual se genera la predicción |
| `predicted_cu` | CU estimado por el modelo |

### `pipeline_runs`

| Columna | Descripción |
|---|---|
| `run_id` | UUID único de la ejecución |
| `started_at` / `finished_at` | Ventana de ejecución |
| `status` | Resultado del pipeline |
| `duration_seconds` | Duración total |
| `rows_processed` | Registros extraídos y procesados |
| `error_message` | Detalle del fallo, si existió |

Las tablas son creadas por pandas `to_sql` durante la primera ejecución; no se requiere ejecutar migraciones para la demostración local.

## Dashboard

`dashboard/app.py` consulta directamente las tres tablas de PostgreSQL y está dividido en dos áreas.

### Pipeline Monitoring

- Estado y hora de la última ejecución.
- Duración, volumen procesado y cantidad de errores.
- Serie de duración por ejecución.
- Gráfico de volumen procesado.
- Historial completo de ejecuciones y mensajes de error.

### Predicción de Tarifas

- Filtros dependientes por operador de red y nivel.
- Último CU observado y CU predicho.
- Periodo objetivo y variación esperada.
- Histórico de `cu_total` junto con el siguiente valor predicho.
- Tabla completa de predicciones.

La variación se calcula como:

```text
variacion_pct = (predicted_cu - last_cu) / last_cu * 100
```

Las consultas utilizan `st.cache_data` con expiración para reducir accesos repetitivos a PostgreSQL. El botón **Actualizar datos** limpia la caché y vuelve a consultar las tablas. Los errores de conexión se muestran en la interfaz sin romper silenciosamente la aplicación.

## Estructura del proyecto

```text
energy-tariff-pipeline/
├── dashboard/
│   └── app.py             # Dashboard Streamlit
├── data/                   # Datos locales de exploración
├── src/
│   ├── extract.py         # Consumo de la API
│   ├── transform.py       # Limpieza y normalización
│   ├── validate.py        # Reglas de calidad
│   ├── load.py            # Carga de energy_tariffs
│   ├── prepare_model.py   # Fechas, orden y variables rezagadas
│   ├── train_model.py     # Evaluación temporal del modelo
│   ├── predict.py         # Entrenamiento y predicción productiva
│   ├── monitoring.py      # Registro de ejecuciones
│   ├── pipeline.py        # Versión ETL directa, sin Prefect
│   ├── prefect_flow.py    # Flujo completo orquestado
│   ├── profile_data.py    # Perfil exploratorio de la fuente
│   └── test_db.py         # Prueba básica de PostgreSQL
├── docker-compose.yml     # PostgreSQL 16
└── README.md
```

## Instalación y ejecución

### Requisitos

- Python 3.11 o superior.
- Docker Desktop o una instancia accesible de PostgreSQL.
- Acceso a internet para consultar Datos Abiertos Colombia.

### 1. Crear y activar el entorno virtual

Desde la raíz del proyecto:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

En macOS o Linux:

```bash
python -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install pandas requests sqlalchemy psycopg2-binary prefect scikit-learn numpy streamlit plotly
```

### 3. Iniciar PostgreSQL

```bash
docker compose up -d
```

La configuración local definida en `docker-compose.yml` es:

```text
Host: localhost
Puerto: 5432
Base de datos: energy_db
Usuario: energy_user
Contraseña: energy_pass
```

Estas credenciales son adecuadas únicamente para desarrollo o demostración local. En un entorno real deben administrarse mediante secretos o variables de entorno.

### 4. Probar la conexión

```powershell
cd src
python test_db.py
```

### 5. Ejecutar el flujo completo

Desde `src`, para que los imports locales se resuelvan correctamente:

```powershell
python prefect_flow.py
```

Esta primera ejecución crea y llena `energy_tariffs`, `tariff_predictions` y `pipeline_runs`.

También existe una versión ETL simple, sin orquestación ni predicción:

```powershell
python pipeline.py
```

Para la demostración integral se debe usar `prefect_flow.py`.

### 6. Iniciar el dashboard

Vuelve a la raíz del proyecto y ejecuta:

```powershell
cd ..
streamlit run dashboard/app.py
```

Streamlit mostrará la URL local, normalmente `http://localhost:8501`.

El dashboard acepta la variable de entorno `DATABASE_URL`. Si no está definida, utiliza la conexión local configurada en Docker Compose:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://energy_user:energy_pass@localhost:5432/energy_db"
streamlit run dashboard/app.py
```

## Guion breve para una entrevista

Una forma clara de presentar el proyecto en dos minutos:

1. **Problema:** convertir un dataset público de tarifas en información confiable, monitoreada y útil para anticipar el siguiente periodo.
2. **Pipeline:** la API alimenta un ETL con limpieza explícita y validaciones que impiden cargar datos defectuosos.
3. **Confiabilidad:** Prefect divide el proceso en tareas, añade logs, reintenta la extracción y registra tanto éxitos como fallos.
4. **Modelo:** se respeta el orden temporal, se crean tres rezagos y se usa Gradient Boosting para modelar relaciones no lineales por operador y nivel.
5. **Persistencia:** PostgreSQL separa datos limpios, predicciones y telemetría operativa.
6. **Consumo:** Streamlit ofrece una vista ejecutiva para operación y otra analítica para explorar cada serie tarifaria.
7. **Evolución:** como siguiente paso se añadirían tests automatizados, migraciones, manejo centralizado de secretos, evaluación persistida, alertas y un deployment programado de Prefect.

## Decisiones técnicas y trade-offs

- **Carga completa (`replace`) frente a incremental:** simplifica la consistencia para un dataset público de tamaño manejable. Con mayor volumen convendría una carga incremental con claves y `upsert`.
- **Entrenamiento durante cada ejecución:** garantiza predicciones alineadas con la fuente más reciente. En un sistema de mayor escala se desacoplarían entrenamiento e inferencia y se versionaría el modelo.
- **Tres rezagos:** ofrecen señal temporal sin hacer demasiado complejo el prototipo. Se podrían sumar estacionalidad, variables externas y validación con ventanas móviles.
- **PostgreSQL como única fuente del dashboard:** desacopla la visualización del proceso ETL y evita que una visita al dashboard dispare extracciones o entrenamientos.
- **Caché con TTL:** mejora la experiencia de uso sin ocultar la disponibilidad de datos nuevos, porque también existe actualización manual.

## Mejoras para una versión productiva

- Añadir `requirements.txt` con versiones fijadas.
- Centralizar todas las conexiones en variables de entorno o Prefect Blocks.
- Crear índices, restricciones y migraciones de esquema.
- Implementar pruebas unitarias y de integración para transformaciones y calidad.
- Configurar un deployment y schedule de Prefect.
- Añadir alertas ante fallos o degradación de tiempos y volumen.
- Persistir métricas del modelo y comparar versiones antes de promoverlas.
- Aplicar backtesting con ventanas temporales móviles y monitoreo de drift.
- Cambiar la carga completa por una estrategia incremental si crece el volumen.

## Autor

Proyecto desarrollado como demostración técnica de ingeniería de datos, machine learning y visualización analítica.
