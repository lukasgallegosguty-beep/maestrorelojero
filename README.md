# Maestro Relojero

Juego para celular de restauración y armado de relojes mecánicos reales —de un reloj de bolsillo de escuela a un tourbillon y cronógrafos legendarios—, pensado para construirse con **Claude Design** y publicarse en **GitHub Pages** como app instalable (PWA).

## Qué hay en este repositorio

| Ruta | Contenido |
|---|---|
| `00_PROMPT_Claude_Design.md` | Prompt de la Fase 1 para pegar en Claude Design |
| `docs/01_GDD_Maestro_Relojero.md` | Documento de diseño del juego |
| `docs/02_Especificacion_Tecnica.md` | Especificación técnica y criterios de aceptación |
| `docs/03_Prompts_por_Fases.md` | Prompts de las fases 2 a 6, plantilla de errores y control de calidad |
| `data/catalogo_base.json` | Tipos de pieza, síntomas, herramientas, repuestos, defectos y configuración |
| `data/niveles/*.json` | 12 niveles con secuencia exacta de armado y geometría |
| `data/catalogo_completo.json` | Todo lo anterior en un solo archivo |
| `tools/build_catalogo.py` | Script que regenera `data/` |
| `index.html` | Plantilla con el `<head>` listo para PWA (se reemplaza por el juego) |
| `manifest.webmanifest`, `sw.js`, `icons/` | Instalación en el celular y funcionamiento sin conexión |
| `.nojekyll` | Hace que GitHub Pages publique los archivos tal cual |

## Paso a paso

### 1. Crear el repositorio y publicar la plantilla

1. En GitHub: **New repository** → nombre `maestro-relojero` → **Public** (con cuenta gratuita, GitHub Pages solo funciona en repositorios públicos) → **Create repository**.
2. **Add file → Upload files** → arrastra **el contenido** de esta carpeta (no la carpeta) → **Commit changes**.
3. **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `(root)` → Save**.
4. En uno o dos minutos, `https://TU-USUARIO.github.io/maestro-relojero/` muestra la página de espera.

### 2. Construir el juego en Claude Design

1. Abre Claude Design y crea un proyecto nuevo de tipo prototipo.
2. Agrega el contexto de una de estas dos formas:
   - **Recomendada:** vincula este repositorio de código. Si te deja elegir, limita el contexto a `docs/`, `data/` e `index.html`.
   - **Alternativa:** adjunta los archivos de la tabla de la Fase 1 en `00_PROMPT_Claude_Design.md`. Si algún formato no se puede adjuntar, pega su contenido en el chat.
3. Pega el prompt de `00_PROMPT_Claude_Design.md` y revisa que confirme qué archivos leyó.
4. Prueba en el lienzo y corrige con comentarios o con la plantilla de `docs/03_Prompts_por_Fases.md`.
5. Sigue con las fases 2 a 6 en el mismo proyecto.

### 3. Publicar cada versión

1. En Claude Design: **Export → Export as standalone HTML**.
2. Renombra el archivo a `index.html`.
3. En GitHub: **Add file → Upload files** → sube `index.html` a la raíz (reemplaza la plantilla) → **Commit changes**.
4. Si exportaste como `.zip` (varios archivos), descomprímelo y sube todo a la raíz; el archivo principal debe llamarse `index.html`.
5. En `sw.js` cambia `VERSION` (`v1` → `v2` …) cada vez que publiques, para que el celular reciba la versión nueva.

### 4. Instalar en el celular

- **Android (Chrome):** abre la URL → menú ⋮ → **Instalar app** o **Agregar a la pantalla principal**.
- **iPhone (Safari):** abre la URL → **Compartir** → **Agregar a inicio**.

### 5. Modificar o agregar relojes

Los niveles salen de `tools/build_catalogo.py` (Python 3, sin dependencias). Edita o agrega un nivel y ejecuta desde la raíz:

```bash
python3 tools/build_catalogo.py data
```

El script valida que cada nivel tenga al menos 25 piezas, que la cantidad crezca de un nivel al siguiente, que cada puente venga después de sus ruedas, que los tornillos no choquen entre sí y que todo quepa en la platina. Luego pega el JSON del nivel nuevo dentro de `CATALOGO.niveles` del juego (o pídeselo a Claude Design).

## Problemas frecuentes

| Problema | Solución |
|---|---|
| La URL da 404 | Espera 2 minutos; revisa que `index.html` esté en la raíz y que el repositorio sea público |
| Sigo viendo la versión anterior | Sube `VERSION` en `sw.js`; cierra y vuelve a abrir la app |
| No hay sonido en el iPhone | Toca la pantalla una vez para activar el audio y revisa el interruptor de silencio |
| La página hace zoom o se desplaza al arrastrar | La mesa debe tener `touch-action: none`; repórtalo con la plantilla de errores |

## Aviso

Las marcas y calibres se mencionan con fines descriptivos y educativos; el juego no está afiliado a ninguna marca. Todas las ilustraciones son esquemáticas y propias.
