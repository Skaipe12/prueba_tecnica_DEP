# Pipeline de micro-batches — Prueba técnica de ingeniería de datos (Pragma)

Pipeline en Python que carga cinco CSV (`2012-1.csv` … `2012-5.csv`) en PostgreSQL por
micro-batches. A la vez mantiene estadísticas en ejecución del campo `price`: recuento,
promedio, mínimo y máximo. Esas estadísticas se actualizan con cada fila nueva y nunca se
recalculan sobre lo ya cargado. Al final se pasa `validation.csv` por el mismo flujo y se
comparan las estadísticas en memoria con una consulta directa a la base de datos, antes y después.

## Contenido de `docs/`

| documento | contenido |
|-----------|-----------|
| [`prueba_tecnica/docs/evidence/`](prueba_tecnica/docs/evidence/) | salidas de consola y consultas a la BD que prueban el resultado |
| [`prueba_tecnica/docs/notebook/demo_pipeline.ipynb`](prueba_tecnica/docs/notebook/demo_pipeline.ipynb) | ejecución narrada paso a paso y decisiones de diseño |

---

## Arquitectura

```
prueba_tecnica/
├── .env                                # Configuración local (no versionado)
├── requirements.txt
├── data/                               # CSV del reto
├── docs/                               # Documentación, evidencia y notebook
├── src/
│   ├── main.py                         # Punto de entrada: arma e invoca el servicio
│   ├── config/
│   │   ├── constants.py                # Variables del pipeline leídas del .env
│   │   ├── env.py                      # Conexión a PostgreSQL leída del .env
│   │   └── logger.py                   # Configuración única del logging (sin .env)
│   ├── queries/
│   │   └── queries.py                  # PipelineQueries: todo el SQL del proyecto
│   ├── resources/
│   │   ├── connections/
│   │   │   └── postgres_connection.py  # PostgresConnection: engine y lecturas puntuales
│   │   ├── csv_loader.py               # CsvLoader: lectura por chunks y limpieza
│   │   ├── batch_partitioner.py        # BatchPartitioner: tamaño y numeración de batches
│   │   ├── metric_analyzer.py          # RunningStats + MetricAnalyzer: estadísticas O(1)
│   │   ├── schema_manager.py           # SchemaManager: creación y limpieza de tablas
│   │   └── validator.py                # Validator: validación de archivos, chunks y batches
│   ├── services/
│   │   └── pipeline_service.py         # PipelineService: orquestación, run y report
│   └── utils/
│       └── utils.py                    # Conversión a Decimal/int, redondeo y formato de logs
└── tests/                              # Tests unitarios (sin base de datos)
```

`PipelineService` recibe todos sus colaboradores por constructor (inyección de dependencias).
`src/main.py` es el único lugar donde se instancian. Los recursos no escriben SQL ni deciden
qué se registra en el log: devuelven datos y el servicio decide qué contar.

### Flujo

```
Validator.validate_inputs()  ¿existen los CSV del reto y validation.csv? Si no, se detiene antes de crear el pipeline
setup()        create_tables → load_from_db
run()          por cada archivo (ordenado por nombre):
                 ¿ya está en transactions.source_file? → WARNING y se omite
                 ┌ una transacción por archivo ──────────────────────────┐
                 │ por cada batch:                                       │
                 │   INSERT de las filas del batch (executemany)         │
                 │   MetricAnalyzer.update_batch(prices)  ← en memoria   │
                 │ UPSERT de pipeline_stats, una vez, al final           │
                 └ commit, o rollback y se detiene el pipeline ───────────┘
report()       estadísticas en memoria vs. COUNT/AVG/MIN/MAX sobre transactions
run_validation()  run([validation.csv])
```

---

## Instalación y ejecución desde cero

Requisitos: Python 3.11 o superior y PostgreSQL instalado localmente. Todos los comandos
se ejecutan desde la raíz del proyecto (`prueba_tecnica/`).

### 1. Entorno virtual y dependencias

```powershell
python -m venv env_proyecto
.\env_proyecto\Scripts\Activate.ps1        # Linux/macOS: source env_proyecto/bin/activate
pip install -r requirements.txt
```

### 2. Base de datos

Por defecto se usa la base `postgres`, que ya existe en toda instalación. Para usar una base
dedicada, créala y cambia `POSTGRES_DB` en el `.env`:

```sql
CREATE DATABASE pragma_pipeline;
```

Las tablas no se crean a mano: el pipeline las crea al arrancar. Al volver a ejectuar el pipeline pregunta si la b.d ya existe y si sí entonces no la crea


El logging no depende del `.env`: su nivel está en `src/config/logger.py` (`LOG_LEVEL`) y la
salida es solo por consola. Para ver una línea por batch, cambia `LOG_LEVEL` a `"DEBUG"` ahí.

Los CSV se leen de la carpeta `data/` de la raíz del proyecto; la ruta está fija en
`src/config/constants.py`. Copia ahí los seis archivos.

### 3. Ejecutar

```powershell
python -m src.main
```

La salida esperada está en [`docs/evidence/01_primera_ejecucion.log`](prueba_tecnica/docs/evidence/01_primera_ejecucion.log).
Termina con dos reportes en `consistent: True`. En ambos las estadísticas en memoria y la
consulta a la BD dan los mismos valores:

| momento               | filas en BD | count | avg     | min | max |
|-----------------------|------------:|------:|---------|----:|----:|
| tras los 5 archivos   | 143         | 139   | 57.8849 | 10  | 100 |
| tras `validation.csv` | 151         | 147   | 57.0068 | 10  | 100 |

`filas en BD` incluye las 4 filas con `price` NULL, que se conservan en `transactions`.
`count` solo considera las filas con precio, que son las que alimentan las estadísticas.

Si lo ejecutas de nuevo, el pipeline reanuda el estado y omite los archivos ya cargados.
Para volver a empezar desde cero:

```powershell
python -c "from src.main import build_pipeline; build_pipeline().schema.drop_tables()"
```

### 4. Tests

```powershell
pytest
```

Son 26 tests unitarios de la lógica pura (`MetricAnalyzer`, `CsvLoader`, `BatchPartitioner`)
y no necesitan base de datos.

### 5. Notebook de demostración

[`docs/notebook/demo_pipeline.ipynb`](prueba_tecnica/docs/notebook/demo_pipeline.ipynb) ejecuta el pipeline paso a paso
y muestra cómo evolucionan las estadísticas. Abrirlo requiere un kernel de Jupyter, que no es
dependencia del pipeline (`pip install ipykernel`). La celda con `RESET = True` reinicia las
tablas antes de cargar.


## 6. Logging

Cada nivel tiene un uso fijo:

- **INFO:** el batch size y las tablas creadas al arrancar, un resumen al terminar cada archivo
  (filas, filas sin precio, descartadas y estadísticas) y los reportes de verificación.
- **DEBUG:** una línea por batch con su número y sus filas.
- **WARNING:** archivos omitidos por ya cargados y filas descartadas por timestamp inválido,
  con su motivo.
- **ERROR:** fallo al cargar un archivo, con la traza, el rollback y la detención del pipeline.
