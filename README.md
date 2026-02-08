# Reporte Electoral (GitHub Pages)

Este repo genera un **reporte diario** (imagen PNG) a partir del archivo Excel `data/Encuestas_2025.xlsx` y lo publica automáticamente en **GitHub Pages**.

## Cómo funciona
- `generator/generate_report.py` lee el Excel y genera:
  - `dist/assets/dashboard.png`
  - `dist/assets/latest.json`
  - `dist/index.html`
- El workflow `.github/workflows/daily.yml` corre **diario** (y manual con *Run workflow*) y publica `dist/` en Pages.

## Requisitos
- Python 3.11+
- Dependencias: ver `generator/requirements.txt`

## Uso local
```bash
pip install -r generator/requirements.txt
python generator/generate_report.py
```
Luego abre `dist/index.html`.

## Actualizar datos
Reemplaza el archivo `data/Encuestas_2025.xlsx` por una versión nueva (commitea y push). El workflow diario también lo regenerará.

## Notas
- Este MVP **no depende de Google Drive/Colab**.
- Los mapas por polígonos no se incluyen porque no tenemos el GeoJSON; en su lugar se muestra el **ganador por macroregión** usando la hoja `zonificado` si existe.
