# mi-primer-repo

Repositorio de práctica para aprender el flujo de trabajo con Git y GitHub: ramas, commits y pull requests.

## Imágenes para presentaciones (Pexels y Pixabay)

`herramientas/imagenes.py` busca y descarga fotos gratuitas de **Pexels** y **Pixabay**
para usarlas en presentaciones. Solo necesita Python 3 (sin dependencias).

### Configuración (una sola vez)

1. Crea tus claves gratuitas:
   - Pexels: <https://www.pexels.com/api/>
   - Pixabay: <https://pixabay.com/api/docs/> (la clave aparece al iniciar sesión)
2. Guárdalas como variables de entorno `PEXELS_API_KEY` y `PIXABAY_API_KEY`.
   En Claude Code en la nube: menú del entorno → *Edit* → secretos / variables de entorno.
3. Si el entorno tiene acceso de red limitado, añade estos dominios permitidos:
   `api.pexels.com`, `images.pexels.com`, `pixabay.com`, `cdn.pixabay.com`.

### Uso

```bash
# Ver resultados de ambas fuentes (horizontales por defecto)
python3 herramientas/imagenes.py buscar "trabajo en equipo"

# Descargar 3 imágenes de cada fuente en imagenes/
python3 herramientas/imagenes.py descargar "seguridad industrial" -n 3 --destino imagenes/

# Solo una fuente, cualquier orientación
python3 herramientas/imagenes.py buscar "naturaleza" --fuente pixabay --orientacion cualquiera
```

Cada descarga añade una entrada en `creditos.json` (autor, enlace y texto de crédito,
p. ej. *"Foto de Ana en Pexels"*) para citarlo en la diapositiva o al final.
Ambas licencias permiten uso gratuito, también comercial; el crédito no es obligatorio pero se agradece.
