# PROMETHEUS — Misión 03 · Coevaluación

Aplicación Streamlit para la coevaluación de la Misión 03.

## Flujo
1. El alumno ingresa su ID institucional.
2. La aplicación identifica su equipo mediante `estudiantes.csv`.
3. El alumno selecciona el rol que desempeñó en la Misión 03. No es necesario registrar los roles de los compañeros.
4. Evalúa a cada compañero, excepto a sí mismo, con cinco criterios ponderados.
5. Envía la coevaluación.
6. El registro se guarda en GitHub mediante la API.
7. La aplicación genera un comprobante PDF con fecha, hora, equipo, rol, número de compañeros evaluados y código de comprobación. No muestra las puntuaciones de los compañeros.

## estudiantes.csv
Columnas mínimas:

```csv
id,nombre_completo,mision03
```

La columna `rol` puede existir, pero la aplicación ya no depende de ella: cada alumno selecciona su propio rol dentro de la app.

## Streamlit Secrets

```toml
GITHUB_TOKEN = "tu_token"
GITHUB_REPO = "Alejandra-LozC/mision03"
GITHUB_BRANCH = "main"
```

El token no debe incluirse en el repositorio.
