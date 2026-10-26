# Maestro Relojero — Prompts por fases y control de calidad

Un juego de este tamaño sale mejor por capas. Usa el mismo proyecto de Claude Design y avanza fase por fase. Antes de cada fase nueva, pide a Claude Design: **«Guarda lo que tenemos como versión estable»**.

| Fase | Qué agrega | Archivos que adjuntar o tener en el repositorio |
|---|---|---|
| 1 | Banco de trabajo completo, niveles 1 y 2 | GDD, especificación, `catalogo_base.json`, `n01`, `n02`, `index.html` plantilla (prompt en `00_PROMPT_Claude_Design.md`) |
| 2 | Reparación y flujo completo del encargo | Los mismos (los defectos ya están en el catálogo) |
| 3 | Progresión: tienda, reputación, desbloqueos; niveles 3 a 6 | `n03` a `n06` |
| 4 | Precisión: cronocomparador, regulación, modo Maestro; niveles 7 a 9 | `n07` a `n09` |
| 5 | Cronógrafos; niveles 10 a 12 | `n10` a `n12` |
| 6 | Pulido, tutorial, accesibilidad y publicación | — |

---

## Fase 2 — Reparación y flujo completo del encargo

```text
Fase 2 de «Maestro Relojero». Mantén todo lo que funciona. Agrega el flujo completo del encargo según la sección 2 del GDD y la 15 de la especificación: Recepción → Diagnóstico → Desarmado → Limpieza y reparación → Armado → Prueba → Encajado → Entrega.

1. Diagnóstico: probar la marcha del reloj tal como llega, mirar con lupa (zoom) y anotar los defectos del nivel (lista «defectos» del catálogo). Los defectos se ven en las piezas: suciedad, rayas, grietas, óxido, pieza dañada.
2. Desarmado: secuencia inversa del nivel; desatornillar exige el gesto circular; las piezas van a la mesa y la bandeja. Después de la primera vez, ofrece «desarmado rápido».
3. Mini-juegos de reparación (tabla de la sección 9 del GDD): limpiar con pera y pincel, pulir frotando, sellar la grieta de un cristal acrílico trazándola con resina y curando con UV, reemplazar cristal midiendo y presionando, cambiar la pila con la polaridad correcta, limpiar contactos, desmagnetizar, reemplazar una pieza dañada, cambiar junta y correa, e «informar al cliente» ante un pelo en el esmalte.
4. Si una herramienta necesaria no está comprada, muestra qué falta y su precio (la tienda completa llega en la Fase 3; por ahora habilita las herramientas iniciales y las de los niveles 1 y 2).
5. La prueba de marcha debe reflejar los defectos pendientes (efecto de cada defecto) además de las piezas faltantes.
6. Los defectos resueltos mejoran estrellas y pago; los no resueltos bajan la satisfacción del cliente.
Al terminar, resume lo hecho y lo pendiente.
```

## Fase 3 — Progresión, tienda y niveles 3 a 6

```text
Fase 3 de «Maestro Relojero». Agrega al CATALOGO los niveles n03_catalina_caracol, n04_hamilton_992b, n05_seiko_nh35 y n06_eta_2824_2 (adjuntos), sin cambiar su contenido.

1. Tienda con herramientas y repuestos del catálogo (precios en pesos chilenos). Cada herramienta habilita su efecto (por ejemplo, lupas = zoom máximo, pinzas antimagnéticas = paso fino de 0,75 px).
2. Reputación, estrellas y fórmula de pago de la sección 16 de la especificación; desbloqueo de cada nivel cuando el anterior está entregado y se tienen sus «herramientas_requeridas».
3. Trabajos rápidos repetibles (lista «trabajosRapidos»), para juntar dinero.
4. Días de taller y plazo de cada cliente; el atraso descuenta el pago.
5. Vitrina con una tarjeta por reloj entregado y Enciclopedia de piezas y calibres (se desbloquean al usarlas).
6. Mecánicas nuevas de estos niveles: pasadores (presionar con pinzas), cadena del caracol (trazar su recorrido del barrilete al caracol), llave de cuerda, resortes que requieren pinzas, puesta en hora por palanca, automático con rotor que se coloca al encajar, calendario, ruedas inversoras, bridas de encajado y alineación de pivotes (sección 10 de la especificación).
Al terminar, resume lo hecho y lo pendiente.
```

## Fase 4 — Precisión: regulación, modo Maestro y niveles 7 a 9

```text
Fase 4 de «Maestro Relojero». Agrega los niveles n07_hamilton_h40, n08_rolex_3135 y n09_tourbillon.

1. Cronocomparador (sección 14 de la especificación): marcha en s/día, amplitud, error de ritmo y gráfico de puntos en vivo.
2. Regulación: raqueta, raqueta micrométrica (pasos finos), tuercas Microstella por pares opuestos (si no son opuestas, aumenta el error de ritmo) y ajuste de puesta en marcha. Meta ±10 s/día; en el N08, −4/+6 s/día (cronómetro).
3. Dificultad Maestro: tolerancias finas, sin ayudas de orientación, tornillos que se pasan de rosca, resortes que saltan (siempre a un punto visible de la mesa) y pivotes que se quiebran si se atornilla sin alinearlos.
4. Tourbillon: las piezas con «modulo: jaula_tourbillon» se arman con zoom automático (lupa ×10) sobre la jaula; en la prueba de marcha, la jaula gira una vuelta por minuto.
5. Día y fecha, fecha instantánea con su resorte y tornillos de pie de esfera que se colocan desde el reverso.
Al terminar, resume lo hecho y lo pendiente.
```

## Fase 5 — Cronógrafos y niveles 10 a 12

```text
Fase 5 de «Maestro Relojero». Agrega los niveles n10_valjoux_7750, n11_omega_321 y n12_zenith_el_primero.

1. Pulsadores de la caja: arranque/parada y puesta a cero.
2. Prueba del cronógrafo: arrancar, detener y volver a cero; el segundero central y los contadores se animan; los síntomas de las piezas de cronógrafo (efectos CRONO_*) se muestran al fallar.
3. Leva de conmutación con piñón oscilante (N10) y rueda de pilares con embrague horizontal (N11 y N12): cada pulsación hace avanzar la rueda de pilares un diente con animación.
4. Tornillo excéntrico del embrague: girarlo ajusta la profundidad de engrane con una marca de referencia.
5. Cristal acrílico como pieza aparte (N11) y frecuencia de 36.000 A/h (N12: 10 golpes por segundo).
Al terminar, resume lo hecho y lo pendiente.
```

## Fase 6 — Pulido y publicación

```text
Fase 6 de «Maestro Relojero». No agregues contenido nuevo: pule y prepara la publicación.

1. Tutorial guiado en el N01 que enseña cada gesto con indicaciones cortas sobre la pantalla.
2. Ajustes: dificultad, volúmenes separados, vibración, modo zurdo, texto grande, alto contraste, reducir movimiento, giro con redondeo a 15°, exportar/importar partida y reiniciar.
3. Rendimiento: revisa que se mantengan 60 fps con 77 piezas (N12) en un teléfono de gama media; menos de 2.500 nodos SVG.
4. Recorre la lista de criterios de aceptación (sección 20 de la especificación) y corrige lo que falle.
5. Créditos con el aviso: «Marcas mencionadas con fines descriptivos; juego no afiliado».
6. Verifica que todo funciona como un único index.html con rutas relativas, y deja el <head> con el manifest, el ícono y el registro de sw.js.
Al terminar, entrega una lista de lo verificado.
```

---

## Plantilla para corregir errores

```text
Hay un problema en «Maestro Relojero».
Dónde: [pantalla / nivel / paso]
Qué hice: [gesto o botones, en orden]
Qué esperaba: [...]
Qué pasó: [...]
Equipo: [modelo de teléfono y navegador]
Corrígelo sin cambiar nada más y dime qué modificaste.
```

## Alternativa: pasar a Claude Code

Si el proyecto crece más de lo que Claude Design maneja con comodidad, usa **Export → Handoff to Claude Code** y continúa ahí con este pedido:

```text
Implementa el juego del paquete de diseño en el repositorio [usuario/maestro-relojero], respetando docs/ y data/ como fuente de verdad. Separa el código en módulos (src/), genera un index.html final con un paso de build simple y verifica los criterios de aceptación de docs/02_Especificacion_Tecnica.md. Al terminar, haz commit y push a main.
```

---

## Control de calidad en el celular (después de cada fase)

1. Abre la URL de GitHub Pages en el teléfono, en vertical.
2. Juega el N01 completo usando solo un dedo.
3. Lleva un puente grande a cada borde: debe achicarse y no salir de la pantalla.
4. Suelta un tornillo encima de la barra inferior: debe volver a la mesa.
5. Usa pinzas: cada toque mueve un paso fino hacia el dedo.
6. Aprieta el tornillo de la rueda de corona: solo debe entrar girando en sentido antihorario.
7. Espera 5 minutos jugando: aparece una pista. Sal de la app 1 minuto: el contador no avanza.
8. Prueba la marcha sin el áncora (tren desbocado) y completo (tic-tac a 5 golpes por segundo).
9. Cierra el navegador y vuelve: el progreso sigue ahí.
10. Activa el modo avión y abre la app desde la pantalla de inicio: debe cargar.
