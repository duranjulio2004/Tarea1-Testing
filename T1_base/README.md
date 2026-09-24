# Tarea 1 — Agente de generación de tests (IIC3745)

Uso: `python agent.py <archivo.py> <carpeta_salida>` → escribe `test_<Modulo>.py` y `metrics.json`.
Requiere `GEMINI_API_KEY` en `.env` (ver `.env.example`) y `pip install -r requirements.txt`.

## Estrategia
1. **Generación** (`prompt_builder.py`): el prompt incluye el código del archivo objetivo **y de todos los
   `.py` de su proyecto** (menos `__init__.py`), para que el modelo no invente el comportamiento de clases
   que el objetivo usa pero no define. Pide explícitamente cubrir ambas ramas de cada `if`/loop, casos de
   borde y particiones de equivalencia, y usar `numpy.random.RandomState(seed)` real en vez de mocks.
   También exige testear el comportamiento **real** del código (no el que sugieren sus nombres): si lanza
   una excepción, afirmarla con `pytest.raises`; y si un bug deja código inalcanzable, reemplazar con
   `monkeypatch` *solo* ese helper roto en tests aparte para ejecutar el resto (caso `tree/tree.py`).
2. **Ciclo de corrección**: una sola sesión de chat con `gemini-3.1-flash-lite`; si pytest falla se envía la
   salida del error y el modelo corrige (máx. 5 intentos). Si la primera llamada falla, los reintentos
   reenvían el prompt completo (no un "arregla esto" sobre una conversación sin código fuente, lo que
   hacía alucinar APIs inexistentes). Se guarda la mejor versión vista (más tests pasando).
3. **Poda**: si tras los reintentos aún hay tests fallando, el agente elimina automáticamente esas funciones
   (vía AST) y mide con las que pasan. Un solo test malo ya no deja todas las métricas en 0, y un test que
   siempre falla no infla el mutation score "matando" todos los mutantes.
4. **Métricas**: `coverage run --branch` para líneas/ramas; `cosmic-ray` para mutation score.

## Decisiones de diseño
- **Imports**: los proyectos mezclan `from blackjack import X` y `from utils import X`. El agente genera un
  `conftest.py` que agrega al `sys.path` la carpeta del archivo (primero) y su carpeta padre, con rutas
  relativas al propio conftest (funciona tras copiar/descomprimir). El orden importa: al revés,
  `svm/svm.py` importaría el paquete `svm/__init__.py` en vez del módulo. Si el proyecto es un paquete, el
  conftest además lo importa primero: `gin_rummy` tiene un import circular (`action_event` → `gin_rummy` →
  … → `move` → `from action_event import *`) que solo se resuelve si `__init__` es el punto de entrada.
- **Presupuesto de 4 minutos**: cada llamada a Gemini tiene timeout propio y los reintentos se detienen 60 s
  antes del límite para dejar tiempo a cobertura y mutación, que también se acotan al tiempo restante.
- **Errores de la API**: si Gemini nunca entrega una suite por `503`/`504`/timeout, el agente muestra el
  error en consola y escribe `{"error": "High demand"}` en `metrics.json` (falla de la API, no del agente).
- **Mutación en paralelo y aislada**: `cosmic-ray` (distribuidor `local`) muta el archivo *en disco* y es
  secuencial. El agente copia el proyecto a N carpetas temporales (N = núcleos, máx. 8), reparte los
  mutantes entre ellas y los ejecuta en paralelo; el código original nunca se modifica. El timeout por
  mutante es 3× lo que tarda la suite (mín. 3 s). Antes de mutar se verifica que la suite pase en la copia.
- **Resultados parciales**: cosmic-ray ejecuta los mutantes en orden aleatorio, así que si se acaba el tiempo
  el puntaje sobre los mutantes completados es una muestra aleatoria (se informa cuántos se midieron).

## Limitaciones encontradas
- **Disponibilidad de Gemini**: `gemini-3.1-flash-lite` devuelve `503 UNAVAILABLE` con frecuencia, a veces
  por minutos. Si no responde dentro del presupuesto, no hay suite y se reporta `"High demand"`.
- **Mutation score muestreado**: en archivos con suites lentas (p. ej. `tree/tree.py`, que entrena árboles
  con numpy/scipy) puede no alcanzar a ejecutarse todo; el puntaje es una estimación.
- **Bugs en el código bajo prueba**: `tree/tree.py` usa `^ 2.0` (XOR) en `_find_splits`, así que `train()`
  lanza `TypeError` con datos reales. El agente lo detecta y lo testea, pero la cobertura queda limitada.
- **`cosmic-ray.toml` del enunciado**: usa un esquema antiguo (`execution-engine`, `test-runner`) que la
  versión actual (8.7) no acepta; el agente genera su propia configuración. Además cosmic-ray ejecuta el
  comando con `shlex.split`, por lo que rutas con espacios deben ir entre comillas.
- **Tests eliminados por la poda**: reflejan casos donde el modelo supuso un comportamiento que el código no
  tiene (p. ej. llamar `predict()` antes de `fit()` en `svm`, o etiquetas `float` en `tree`); se pierde esa
  cobertura en vez de "arreglar" el test a mano.
- **`run_all.sh`**: se adaptó para bash 3.2 (macOS no soporta `declare -A`).
