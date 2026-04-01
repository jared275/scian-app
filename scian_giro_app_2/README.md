# Buscador de giros SAT → SCIAN

Aplicación web local para que un ejecutivo pegue el giro visto en la constancia de situación fiscal, o escriba una descripción libre, y reciba sugerencias SCIAN navegables por:

- Sector
- Subsector
- Rama
- Subrama

## Qué hace

- Calcula similitud sobre los 4 niveles de la jerarquía SCIAN.
- Propone una ruta inicial automática con el mejor camino encontrado.
- Muestra primero los sectores más convenientes y deja profundizar por click.
- Autocompleta el mejor hijo dentro de la opción elegida para reducir navegación.
- Permite cambiar cualquier nivel sin perder la lógica de similitud.
- Permite copiar el recorrido sugerido cuando ya llegaste a Subrama.

## Enfoque de búsqueda

La app usa un ensamble de:

- TF-IDF por palabras
- TF-IDF por caracteres
- fuzzy matching
- promoción jerárquica del mejor nivel encontrado
- expansión semántica para términos comunes de negocio

No requiere API key.

## Experiencia de uso

La vista principal está pensada como un explorador guiado:

1. La búsqueda arma una ruta inicial.
2. Se muestran los sectores sugeridos.
3. Al elegir una opción, la app abre automáticamente el camino más conveniente dentro de esa rama.
4. El ejecutivo puede corregir Sector, Subsector, Rama o Subrama con un click.

Esto reduce la sobrecarga visual frente a una vista con demasiadas coincidencias simultáneas.

## Estructura

- `main.py`: servidor FastAPI
- `search_engine.py`: carga del catálogo y lógica de similitud
- `search_config.py`: diccionario de expansiones semánticas y reglas de ayuda
- `data/catalogo_scian_subrama.csv`: catálogo fuente SCIAN
- `static/`: interfaz web

## Ejecución

1. Crea y activa un entorno virtual.
2. Instala dependencias:

```bash
pip install -r requirements.txt
```

3. Inicia la aplicación:

```bash
uvicorn main:app --reload
```

4. Abre en el navegador:

```text
http://127.0.0.1:8000
```

También puedes abrir con una consulta precargada:

```text
http://127.0.0.1:8000/?q=dentista
```

## Notas

- El CSV fuente trae varias descripciones sin acentos y con artefactos de codificación al final de algunas palabras. La app las normaliza para no afectar la búsqueda y limpia parte de esos residuos para la visualización.
- Si después quieren afinar la calidad, lo más recomendable es retroalimentar `search_config.py` con nuevos alias y vocabulario real observado por los ejecutivos.
