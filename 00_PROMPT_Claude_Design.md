# Prompt para Claude Design — Fase 1

Copia todo el bloque de abajo en el chat de un proyecto nuevo de Claude Design (tipo prototipo), después de vincular el repositorio o adjuntar los archivos indicados.

```text
Rol: actúa como diseñador/a de juegos y desarrollador/a front-end senior, especialista en juegos táctiles para celular.

Objetivo: crea la primera versión jugable de «Maestro Relojero», un juego en español para celular donde soy relojero en un taller: rearmo y reparo relojes mecánicos reales, pieza por pieza y en orden exacto (referencia de género: Watch Restoration, de Steam). Esta entrega es la FASE 1: el banco de trabajo completo y los niveles 1 y 2. Debe poder publicarse en GitHub Pages y jugarse en el navegador del teléfono.

Contexto (léelo antes de empezar y confirma en una línea qué archivos pudiste leer):
- docs/01_GDD_Maestro_Relojero.md → qué es el juego: mecánicas, progresión, arte y audio.
- docs/02_Especificacion_Tecnica.md → cómo implementarlo: coordenadas, gestos, fórmulas, validación y criterios de aceptación.
- data/catalogo_base.json → tipos de pieza (nombre, función, material, síntoma si falta), efectos, herramientas y configuración.
- data/niveles/n01_unitas_6497.json y data/niveles/n02_miyota_2035.json → secuencias exactas de armado con geometría.
- index.html (plantilla) → usa su <head> como base.
El catálogo es la fuente de verdad: no inventes piezas, nombres ni orden. Las piezas con el mismo «paso» se colocan en cualquier orden entre sí; los pasos van en orden estricto.

Restricciones técnicas:
1. Un solo index.html autocontenido: HTML + CSS + JavaScript sin frameworks, sin CDN y sin imágenes ni sonidos externos. La escena es un SVG dibujado por código según forma.t de cada pieza. Sonidos sintetizados con Web Audio API.
2. Incrusta los datos como const CATALOGO = {…catalogo_base, niveles:[n01, n02]} (sin fetch), de modo que agregar un nivel sea pegar su JSON.
3. Mobile-first en vertical (360–430 px de ancho), usable también en horizontal y en escritorio. Pointer Events con multitouch, touch-action:none en la mesa, sin zoom accidental del navegador ni «pull to refresh», respetando el notch (safe-area).
4. Guardado automático en localStorage (clave relojero_save_v1).
5. Rutas relativas. En el <head>: manifest.webmanifest, icons/apple-touch-icon.png y registro de ./sw.js dentro de try/catch (esos archivos ya existen en el repositorio).
6. 60 fps en gama media: sin filtros SVG pesados, sombras como elipses semitransparentes, animar solo transformaciones.

Alcance de la Fase 1:
1. Pantallas: Inicio (Continuar / Nueva partida / Ajustes) → Taller mínimo (encargos N01 y N02 disponibles; N03 a N12 con candado y su requisito visible, tomados de resumenNiveles) → Ficha del encargo (cliente, reloj, calibre, ficha técnica, historia, «¿Sabías que?») → Banco de trabajo → Resultado (estrellas, tiempo, pistas, errores y pago en pesos chilenos).
2. Banco de trabajo: el movimiento en el portamovimientos al centro y las piezas alrededor, como en una mesa de relojero con tapete. Lo listado en «preensamblado» ya viene puesto.
3. Ver armado (estilo memorice): al iniciar muestra el reloj completo, primero por detrás y luego por delante, durante memorice_s del nivel; después las piezas salen volando a la mesa. Botón para volver a verlo (1 uso gratis, enfriamiento 60 s).
4. Manipulación: tocar para seleccionar; arrastrar con un dedo (la pieza va 48 px sobre el dedo); rotar con dos dedos y con botones de 15°; espejo (dar vuelta la pieza); pinzas (cada toque mueve la pieza un paso fino hacia el punto tocado y mantener la mueve lento); atornillar y desatornillar con gesto circular respetando vueltas y rosca izquierda; ficha de la pieza (nombre, función, material y qué pasa si falta) al mantener presionado o con ⓘ.
5. Lista de piezas en hoja inferior, con estado y filtros; tocar un ítem trae la pieza junto al reloj y la selecciona. Botón «Ordenar mesa».
6. Regla de bordes: ninguna pieza puede salir de la pantalla ni quedar bajo el HUD o las barras; las piezas grandes se achican al acercarse al borde y recuperan su tamaño al alejarse (fórmula de la sección 9 de la especificación). Área táctil mínima de 44 px.
7. Voltear el reloj (frente/reverso) con animación; las piezas del otro lado no se dibujan.
8. Validación del orden exacto con tolerancias (dificultad Oficial por defecto) y mensajes claros: «Casi: gírala», «Está al revés», «Va del otro lado: voltea el reloj», «Todavía no: falta algo debajo».
9. Pistas: una cada 5 minutos de juego activo (botón con anillo de progreso); resalta la pieza siguiente y muestra su fantasma en el lugar exacto.
10. Probar marcha: dar cuerda con la corona; si está completo, el volante oscila y el tic-tac suena a la frecuencia del calibre (18.000 A/h = 5 golpes por segundo; el cuarzo salta 1 vez por segundo); si falta algo, muestra el síntoma de mayor prioridad de la tabla «efectos», con su animación.
11. Sonidos sintetizados (tabla de la sección 17), vibración corta si el equipo la soporta y desbloqueo de audio en el primer toque (iOS).
12. Dinero básico: el pago se acredita al entregar y queda guardado.

Dirección visual: taller de relojería cálido y preciso. Tapete verde oscuro, luz cenital, latón dorado, acero rodiado con Côtes de Genève, platina con perlage, tornillos azulados y rubíes rojos. Títulos con serif clásica e interfaz sans legible. Ilustraciones esquemáticas propias.

Regla de marcas: las marcas y calibres reales aparecen solo como texto en fichas e historias. No dibujes logotipos ni nombres de marca en esferas, rotores o puentes, ni copies el diseño de cajas o esferas de modelos reales.

Al terminar: deja el juego funcionando en el lienzo y escribe un resumen breve con lo hecho, lo pendiente y cómo probarlo en el celular. Si algo no alcanza en esta fase, prioriza en este orden: puntos 2, 4, 6, 8, 3, 7, 5, 10, 9, 11, 1 y 12.
```

## Archivos que necesita esta fase

| Archivo | Para qué |
|---|---|
| `docs/01_GDD_Maestro_Relojero.md` | Diseño del juego |
| `docs/02_Especificacion_Tecnica.md` | Implementación y criterios de aceptación |
| `data/catalogo_base.json` | Tipos de pieza, efectos, herramientas, configuración |
| `data/niveles/n01_unitas_6497.json` | Nivel 1 (29 piezas) |
| `data/niveles/n02_miyota_2035.json` | Nivel 2 (34 piezas) |
| `index.html` (plantilla) | `<head>` con manifest, ícono y service worker |

Las fases siguientes están en `docs/03_Prompts_por_Fases.md`.
