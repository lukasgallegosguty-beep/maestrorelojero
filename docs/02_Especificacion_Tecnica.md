# Maestro Relojero — Especificación técnica v1.0

Complementa al GDD (`docs/01_GDD_Maestro_Relojero.md`). Los valores numéricos configurables están en `config` de `data/catalogo_base.json`; si hay diferencia, manda el catálogo.

---

## 1. Stack y restricciones

| Tema | Decisión |
|---|---|
| Entregable | Un `index.html` autocontenido: HTML + CSS + JavaScript vanilla (ES2020). Sin frameworks, sin CDN, sin imágenes ni sonidos externos |
| Escena | Un `<svg>` con cámara (pan/zoom). Todo se dibuja por código a partir de `forma.t` |
| Datos | `const CATALOGO = { ...catalogo_base, niveles: [ ...niveles ] }` incrustado. Agregar un nivel = pegar su JSON en `niveles` |
| Audio | Web Audio API, todo sintetizado |
| Guardado | `localStorage`, clave `relojero_save_v1` |
| PWA | `<link rel="manifest" href="manifest.webmanifest">`, `<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">`, `<meta name="theme-color" content="#1f3b33">` y registro de `./sw.js` dentro de `try/catch`, solo si `location.protocol === 'https:'` |
| Viewport | `width=device-width, initial-scale=1, viewport-fit=cover`; márgenes con `env(safe-area-inset-*)` |
| Gestos del navegador | `touch-action: none` en la mesa; `touch-action: manipulation` en botones; `overscroll-behavior: none` en `body`; `user-select: none`; `-webkit-touch-callout: none`; `preventDefault` de `gesturestart` (iOS) y de `contextmenu` |
| Rutas | Siempre relativas (el sitio vive en `https://USUARIO.github.io/REPO/`) |

## 2. Arquitectura (módulos dentro del mismo archivo)

| Módulo | Responsabilidad |
|---|---|
| `Datos` | Acceso al catálogo: `tipo(id)`, `nivel(id)`, `efecto(código)`, `herramienta(id)` |
| `Estado` | Store con suscripción: partida (dinero, reputación, herramientas…) y banco (piezas, paso actual, vista) |
| `Escena` | SVG, capas, cámara, render de piezas, fantasmas, halos |
| `Formas` | Generadores SVG por `forma.t`, con caché de `path` por pieza |
| `Gestos` | Máquina de estados de punteros (sección 6) |
| `Reglas` | Validación del armado y avance de pasos |
| `Simulacion` | Prueba de marcha, síntomas, cronocomparador |
| `Reparacion` | Mini-juegos (Fase 2) |
| `Audio` | Síntesis y mezcla |
| `UI` | Pantallas, HUD, hojas, avisos (toasts); nunca `alert()` |
| `Guardado` | Autoguardado, exportar e importar |

`requestAnimationFrame` corre solo mientras haya animaciones activas (arrastre, marcha, explosión), para ahorrar batería.

## 3. Coordenadas y capas

- **Mundo:** unidades del catálogo; la platina mide **radio 100**; origen en el centro del movimiento; **y hacia abajo**; ángulos en **grados, sentido horario desde las 12**.
- **Lados:** cada pieza declara `lado`: `reverso` (vista desde el fondo, lado puentes) o `frente` (vista desde la esfera). Sus coordenadas están expresadas tal como se ve ESE lado. Un eje compartido aparece en el otro lado con **x espejada** (`x → −x`).
- **Vista:** `vista ∈ {reverso, frente}`. Las piezas colocadas cuyo `lado ≠ vista` no se dibujan (quedan detrás de la platina), salvo caja, bisel y anillo de encajado, que se ven en ambos lados con x espejada.
- **Pantalla:** `escala = 0,36 × min(anchoMesa, altoMesa) / 100` (el reloj ocupa ~72 % del ancho en vertical). `pantalla = centroReloj + escala × zoom × (x, y) + pan`. Las piezas sueltas viven en el mismo mundo, fuera del radio 100, y se escalan igual (así se comparan tamaños).
- **Transformación de una pieza:** `translate(x,y) rotate(rot) scale(espejo ? −1 : 1, 1) scale(sBorde)`.
- **Capas:** se dibuja por `capa` ascendente y, dentro de la misma capa, por orden de colocación. La pieza que se arrastra va siempre arriba.

## 4. Modelo de datos

### 4.1 Nivel (`data/niveles/*.json`)

`id, orden, dificultad, titulo, reloj{nombre,tipo,ilustracion}, casa, calibre, anio, epoca, specs{…}, historia, sabias_que[], cliente{nombre,perfil,pedido,plazo_dias}, pago_base, reputacion, memorice_s, prob_espejo, rot_spawn_max, orientacion{…}, preensamblado[], mecanicas_nuevas[], herramientas_requeridas[], defectos[], fuentes[], total_piezas, total_pasos, tiempo_objetivo_s, lados_usados[], secuencia[]`

### 4.2 Pieza (cada elemento de `secuencia`)

| Campo | Uso |
|---|---|
| `id` | Único dentro del nivel |
| `tipo` | Clave en `tiposPieza` (nombre, categoría, función, material, `si_falta.efecto`, `requierePinzas`) |
| `nombre` | Opcional: reemplaza el nombre del tipo (p. ej. «Tornillo de la rueda de corona (rosca izquierda)») |
| `lado`, `x`, `y`, `rot` | Objetivo exacto de colocación |
| `rotImporta`, `espejoImporta` | Si la rotación o la cara importan para encajar |
| `capa` | Orden de dibujo |
| `forma` | Geometría para dibujar (sección 5) |
| `paso` | Grupo de orden. Mismo paso = cualquier orden entre ellas |
| `cubre` | (Puentes) ids de las ruedas que sujeta; sus pivotes son los `rubies` |
| `variante`, `sobre`, `tornillo{cabeza_mm, giros, rosca}` | (Tornillos) intercambiables por `variante`; `rosca` derecha o izquierda |
| `pinzas` | Resorte bajo tensión: debe manipularse con pinzas |
| `modulo` | Submódulo (p. ej. `jaula_tourbillon`): zoom automático al llegar a esos pasos |

### 4.3 Estado en juego de cada pieza

```js
{ id, estado: 'bandeja'|'mesa'|'colocada'|'suelta'|'apretada',
  x, y, rot, espejo, sBorde, progresoTornillo, sucia, danada }
```

- **Aparición:** si `rotImporta`, `rot` aleatoria en `±rot_spawn_max` (múltiplos de 15°); si `espejoImporta`, `espejo = true` con probabilidad `prob_espejo`.
- `suelta` solo aplica a tornillos encajados aún sin apretar.

## 5. Dibujo procedural por forma

Todas las formas se generan una vez por pieza y se reutilizan. Materiales por gradiente lineal: `laton` (#E3C27A→#9C7432), `acero` y `rodio` (#E6EAEE→#8F979F), `niquel` (#D8DCDF→#9AA1A7), `oro` (#F1CF7A→#B4862E), `rojo` (#C2343C→#7A1820), `plastico` (#3A3F44→#1F2327), `glucydur` (#D9C9A0→#8F7A4A), `hierro` (#9EA3A8→#5E6468), `circuito` (#2E6B4E con pistas #C9A85A), `aislante` (amarillo translúcido).

| `forma.t` | Parámetros | Cómo dibujarlo |
|---|---|---|
| `rueda` | `r, dientes, brazos, mat, pinon?, estilo?` | Dientes trapezoidales (altura `clamp(r·0,08, 1,2, 3)`); llanta interior `r·0,78`; `brazos` rayos (0 = disco macizo); piñón de acero de radio `pinon`; eje con buje. Estilos: `escape` (15 dientes en gancho), `barrilete` (tambor con tapa), `tambor` (sin dientes), `soleil` (rayos radiales finos), `pinon`, `corredizo` (dientes en ambas caras), `fija`, `fina` (dientes muy finos), `inversora`, `estrella` (7 puntas), `con_dedo` (dedo saliente), `con_corazon` (leva corazón visible), `contrapunto` (dientes perpendiculares) |
| `puente` | `poly, mat, deco, rubies, agujeros` | `path` del polígono local; relleno de material; `deco`: `cotes` (franjas diagonales recortadas), `perlado`, `damasquinado` (arcos), `espejo` (brillo liso), `calado` (perforado y grabado), `liso`; biselado claro de 1 px; rubíes = círculo rojo con chatón dorado; agujeros = círculos oscuros |
| `placa` | `poly, mat, deco, agujeros, cuarzo?` | Como `puente` sin rubíes; `pistas` = líneas del circuito; `cuarzo` = pequeño cilindro plateado |
| `tornillo` | `r, acabado` | Cabeza con gradiente (azulado o pulido) y ranura que gira con el progreso de atornillado |
| `palanca` | `pts, w, mat, curva?, rueda_en?, r_rueda?` | `polyline` con extremos redondeados de ancho `w`; pivote con agujero en `[0,0]`; `curva` suaviza con curvas; `rueda_en` dibuja una rueda de acoplamiento en esa punta |
| `volante` | `r, brazos, espiral, mat, puente?, agujeros?, raqueta?, microstella?, doble_plato?` | Aro grueso, brazos, espiral de Arquímedes de 6 vueltas (`breguet` agrega la curva terminal elevada), tuercas en el aro si `microstella`; si trae `puente`, se dibuja encima con su rubí y agujeros |
| `ancora` | `largo, ancho` | Vástago desde el pivote hacia −y con horquilla en la punta y dos paletas rojas; `rot` la orienta hacia el volante |
| `aguja` | `estilo, largo` | Desde el centro hacia −y. Estilos: `pera, baston, fina, dauphine, espada_luminiscente, flecha, flecha_luminiscente, pala, latigo, escarabajo, poker, breguet, piruleta` |
| `esfera` | `r, estilo, subseg?, contadores?, ventana?{ang,tipo}, apertura?[x,y,r], agujero_cuerda?` | Disco con índices o números según `estilo`; contadores con escala; ventanilla en el ángulo indicado; apertura para tourbillon; agujero de cuerda |
| `disco` | `r_ext, r_int, marcas, ventana_ang` | Anillo con 31 números o 7 días (LUN…DOM) |
| `rotor` | `r, arco, deco` | Media luna con borde pesado y eje central |
| `pila` | `r, codigo` | Moneda plateada; muestra «+» y el código si `espejo = false`, «−» si está dada vuelta |
| `bobina` | `largo, ancho` | Rectángulo con bobinado de cobre |
| `rotor_motor` | `r` | Disco bicolor (imán) |
| `tija` | `largo, corona?` | Vástago con ranura; si `corona`, la corona en el extremo |
| `arandela`, `anillo`, `junta` | `r` / `r_in, r_out` | Anillos finos (acero, polímero, caucho) |
| `caja` | `r, estilo, asas?, colgante?, pulsadores?` | Aro de caja; asas a las 12 y 6 si `asas`; colgante y argolla a las 12 si `colgante`; pulsadores en sus puntos |
| `cristal` | `r, material, abombado?` | Disco translúcido con reflejo; rayas y grietas como capas de defecto |
| `bisel` | `r, con_cristal?, enroscado?` | Aro pulido (con estrías si enroscado) |
| `fondo` | `r, cierre` | `presion` (borde con muesca), `enroscado` (6 muescas), `enroscado_hermetico` (estrías), `exhibicion` (cristal al centro) |
| `caracol` | `r_cono, r_rueda, dientes` | Cono en espiral sobre una rueda dentada |
| `cadena` | `desde, hasta, r_desde, r_hasta` | Eslabones a lo largo de la tangente entre barrilete y caracol |
| `catalina` | `largo, alto, dientes` | Rueda de corona vista de canto: barra con dientes de sierra |
| `platina_superior` | `r, pilares, calados?` | Placa completa con calados y agujeros en los pilares |
| `pasador`, `columna`, `chaton` | `r` | Clavija, columna o chatón con rubí |
| `bloque`, `disco_reglaje`, `raqueta`, `garra`, `leva`, `rueda_pilares`, `jaula` | ver catálogo | Bloque rectangular; disco numerado; raqueta con índice (micrométrica con tornillo y resorte); garra de encajado; leva oblonga; rueda de columnas (`pilares` columnas); jaula de 3 brazos (`parte` inferior o superior) |

**Estados visuales:** seleccionada (halo dorado de 2 px y sombra mayor), fantasma (contorno punteado al 50 %), sucia (manchas semitransparentes), dañada (grieta roja), magnetizada (pequeño ícono de imán), cara B (triángulo en una esquina, solo en Aprendiz y Oficial).

## 6. Gestos (máquina de estados)

- **Pointer Events** con `setPointerCapture`. Hasta 2 punteros activos.
- **Estados:** `REPOSO`, `PRESION_PIEZA`, `ARRASTRE`, `ROTAR_2D`, `PAN_ZOOM`, `PINZAS`, `DIAL_TORNILLO`, `FROTAR` (mini-juegos).
- **Umbrales:** toque ≤ 10 px y ≤ 250 ms; mantener 450 ms; inicio de arrastre > 6 px.
- **ARRASTRE:** la pieza sigue al dedo con **desplazamiento −48 px en Y** (pantalla) para que el dedo no la tape. Al soltar se evalúa el encaje (sección 10); si encaja, se anima el ajuste en 120 ms.
- **ROTAR_2D:** pieza seleccionada + 2 punteros: `rot += Δatan2`. Al soltar, redondeo a 15° si está activado en Ajustes.
- **PAN_ZOOM:** 2 punteros sin pieza seleccionada bajo ellos: `zoom = clamp(zoom × d/d0, 1, zoomMax)` (×1,5 / ×2,5 / ×4 según lupa); pan con el punto medio. Doble toque en mesa vacía vuelve a ×1.
- **Superposición:** el *hit test* devuelve la lista ordenada por capa; un segundo toque en < 600 ms y < 12 px selecciona la siguiente de abajo.
- **Área táctil mínima:** 44 × 44 px (círculo invisible en piezas chicas como tornillos).

## 7. Pinzas (movimiento fino)

```text
activas = herramientaPinzas && piezaSeleccionada
alTocar(P):                                // P = punto en pantalla, fuera de la UI
  dir = normalizar(P − centroPiezaEnPantalla)
  pieza.xy += dir × pasoPx / (escala × zoom)   // pasoPx: 2 (latón) o 0,75 (antimagnéticas)
alMantener: tras 300 ms repetir cada 60 ms
```

- Visual: retícula y dos puntas de pinza sobre la pieza; línea tenue hacia el punto tocado.
- Cruceta opcional (8 direcciones) para accesibilidad.
- Con pinzas la tolerancia de posición suma +2 unidades.
- **Resortes** (`pinzas: true`): si se arrastran con el dedo en Maestro, 30 % de probabilidad de que salten a un punto libre **visible** de la mesa con animación en arco y sonido «tink».

## 8. Rotar y espejo

- Botones ⟲ ⟳: ±15°; mantener repite cada 120 ms.
- ⇋: `espejo = !espejo` con animación `scaleX 1 → 0 → −1` en 180 ms.
- Diferencia angular: `dAng = |((rot − objetivo + 540) mod 360) − 180|`.
- Si `rotImporta = false`, cualquier rotación encaja. Si `espejoImporta = false`, cualquier cara encaja.

## 9. Bordes: encogimiento y contención (requisito clave)

Sea `A` el rectángulo útil de la mesa (pantalla menos HUD, barras y *safe areas*), `L = min(ancho(A), alto(A))`, y de `config.borde`: `Z = 0,18·L` (zona de borde), `G = 0,22·L` (umbral de pieza grande), `MIN = max(56 px, 0,12·L)`, `m = 8 px`.

```text
para cada pieza no colocada (en cada movimiento, al soltar, al cambiar zoom o tamaño de pantalla):
  tam = 2 × radioEnvolvente × escala × zoom          // tamaño en pantalla a escala 1
  d   = distancia del centro de la pieza al borde más cercano de A
  si tam > G:
      t    = clamp(d / Z, 0, 1)
      sMin = max(MIN / tam, 0,35)
      sBorde = sMin + (1 − sMin) × easeOutCubic(t)
  si no:
      sBorde = 1
  r = tam × sBorde / 2
  centro.x = clamp(centro.x, A.izq + m + r, A.der − m − r)
  centro.y = clamp(centro.y, A.sup + m + r, A.inf − m − r)
```

- Ninguna pieza puede quedar fuera de `A` ni bajo el HUD o las barras: si se suelta ahí, vuelve animada al punto válido más cercano.
- Con zoom > 1, las piezas que quedan fuera de vista se marcan con flechas en el borde; tocar una flecha lleva la vista hacia la pieza.
- **Ordenar mesa** las reparte en anillos alrededor del reloj, por paso.
- **Aparición inicial:** anillo alrededor del reloj en orden de paso; lo que no cabe va a la bandeja.
- **Traer desde la lista:** al punto libre más cercano al reloj, ya seleccionada y con un pulso.

## 10. Validación del armado

```text
pasoActual = menor 'paso' con alguna pieza no terminada
             (terminada = 'colocada', o 'apretada' si es tornillo)

alSoltar(pieza):
  objetivos = piezas del pasoActual aún no terminadas y compatibles:
              tornillos y pasadores → misma 'variante'; resto → mismo 'id'
  si no hay objetivos compatibles:
      si la pieza es de un paso futuro y quedó cerca de su objetivo → error + «Todavía no: falta algo debajo»
      terminar
  obj = el más cercano
  si vista ≠ obj.lado → «Esta va del otro lado: voltea el reloj» (sin error)
  dPos  = distancia(pieza, obj) en unidades
  tolP  = tolerancias[dificultad].pos (+2 con pinzas)
  okRot = !obj.rotImporta || dAng ≤ tolerancias[dificultad].rot
  okEsp = !obj.espejoImporta || pieza.espejo == false
  si dPos ≤ tolP y okRot y okEsp → encajar: xy y rot del objetivo; estado 'colocada' ('suelta' si es tornillo); sonido y vibración
  si dPos ≤ tolP y (!okRot o !okEsp) → error + «Casi: gírala» o «Está al revés» (en Maestro solo «No encaja»)
  si tolP < dPos ≤ 3·tolP → «No encaja aún» (sin error)
  si dPos > 3·tolP → queda en la mesa (sin mensaje)

al terminar todas las piezas del pasoActual:
  avanzar; si el próximo paso es del otro lado → chip «Voltea el reloj»
```

- **Retirar (✕):** solo piezas del paso actual o la última colocada.
- **Alineación de pivotes** (desde N06, Oficial y Maestro): al colocar un puente, cada id de `cubre` muestra su pivote en rojo; un toque con pinzas lo asienta (verde). Atornillar con pivotes rojos: aviso; en Maestro se quiebra un pivote (pieza dañada, requiere repuesto).

## 11. Tornillos

- Encajado → `suelta` (cabeza levantada). Seleccionar + 🔩 abre un dial centrado en el tornillo (radio 90 px).
- Ángulo acumulado: `θ += normalizar(atan2_actual − atan2_previo)` (positivo = horario).
- `progreso = clamp(θ × signoRosca / (giros × 360), 0, 1,2)`, con `signoRosca = +1` (derecha) o `−1` (izquierda).
- Tamaño de hoja: igual a `cabeza_mm` → velocidad 100 %; una medida menor → 60 % y 15 % de probabilidad por vuelta de patinar (raya la cabeza: −reputación); mayor → no entra.
- `progreso ≥ 1` → `apretada` (doble clic, vibración 15 ms). Entre 1,1 y 1,2 el indicador de torque se pone rojo; en Maestro, al llegar a 1,2 se pasa la rosca (tornillo dañado).
- Desatornillar: sentido contrario hasta 0 → `suelta` y se puede retirar.
- Accesibilidad: botón «mantener para apretar».
- **Tornillo excéntrico** (`tornillo_excentrico`): `giros` pequeño; en Fase 5 su giro ajusta la profundidad del embrague con una marca de referencia.

## 12. Vista de memoria

1. Todas las piezas se dibujan en su objetivo. Reverso durante `T/2`, giro de 400 ms, frente durante `T/2`, con `T = memorice_s` (+3 s con Manual técnico, mínimo `config.memorice.min_s`).
2. Contador visible y botón «Listo» para saltar.
3. Explosión de 600 ms: cada pieza viaja por una curva hacia su lugar de aparición en la mesa o la bandeja.
4. Sin interacción durante la vista. Repetición: 1 gratis por nivel, luego $2.000 o una pista; enfriamiento 60 s.

## 13. Pistas

```text
cada frame: si pantalla == banco && sin modales && document.visibilityState == 'visible':
              acumulado += dt
            fichas = min(max_acumuladas, fichas + floor(acumulado / intervalo_s)); acumulado %= intervalo_s
```

- `intervalo_s = 300`, `max_acumuladas = 1`, `duracion_s = 6` (de `config.pistas`).
- Efecto: pulso en la pieza correcta del paso actual + fantasma en el objetivo (posición, rotación y cara) + nombre; si está en la bandeja, se resalta su ítem; si hay que voltear, primero el chip «Voltea el reloj».
- Registrar pistas usadas para el pago y las estrellas.

## 14. Simulación de marcha

**Entrada:** piezas terminadas, tornillos apretados, defectos pendientes y reserva de cuerda (0–1).

```text
sintomas = []
para cada pieza del nivel no terminada: sintomas.push(tiposPieza[pieza.tipo].si_falta.efecto)
para cada tornillo en 'suelta': sintomas.push('MARCHA_IRREGULAR')
para cada defecto pendiente: sintomas.push(defectos[id].efecto)
principal = el de menor 'prioridad' en efectos; secundarios = el resto, sin repetir
si es mecánico y reserva == 0 → «Sin cuerda: da cuerda primero»
```

- **Cuerda:** giro circular sobre la corona; +2 % de reserva por cada 30°; clic de trinquete. Automáticos: botón «agitar» (+5 %).
- **Volante:** frecuencia `f = A/h ÷ 7200` oscilaciones completas por segundo; ángulo `α(t) = (amplitud/2) · sen(2πft)`; amplitud sana 280°, baja 180°. Con *reducir movimiento*, volante estático e indicador numérico.
- **Rueda de escape:** avanza 12° por golpe (15 dientes, medio diente por golpe), sincronizada con el sonido.
- **Otras ruedas:** segundos 6°/s; tercera ≈ 0,75°/s; centro 0,1°/s; barrilete ≈ 0,02°/s. Botón «cámara rápida ×10».
- **Tic-tac:** golpes por segundo `= A/h ÷ 3600` (5, 6, 8 o 10). Cuarzo: un paso por segundo.
- **Síntomas animados:** `TREN_DESBOCADO` (ruedas giran rápido 1,5 s y se detienen con zumbido), `VOLANTE_QUIETO` / `NO_ARRANCA` (nada se mueve), `AGUJAS_QUIETAS` (el volante late, las agujas no), `NO_RETIENE_CUERDA` (la barra de reserva cae a cero al soltar), etc.

**Cronocomparador (Fase 4):**

| Condición | Marcha (s/día) | Amplitud | Error de ritmo |
|---|---|---|---|
| Sano y regulado | ±3 | 270–310° | < 0,5 ms |
| `AMPLITUD_BAJA` | −20 | 170–200° | +0,3 ms |
| `ADELANTA_MUCHO` | +300 a +600 | normal | errático |
| `DESREGULADO` | ±45 | normal | normal |
| `FUERA_DE_RITMO` | normal | normal | 2,5 ms |

Regulación: raqueta en `[−1, +1]` → `±90 s/día` lineal (micrométrica con pasos de 1/10); Microstella: 4 tuercas, cada paso ±4 s/día, y girar tuercas no opuestas suma error de ritmo; puesta en marcha: girar el soporte del espiral hasta error < 0,5 ms. Meta: ±10 s/día; en N08 (cronómetro), −4/+6 s/día.

## 15. Reparación (Fase 2)

- Cada encargo copia sus `defectos` a `defectosPendientes`.
- **Frotar** (limpiar, pulir, contactos): máscara de cobertura en grilla 32 × 32 sobre la zona; frotar suma cobertura según velocidad; éxito ≥ 95 %. Sobrepulir (> 130 % en aristas) baja el valor.
- **Trazar grieta:** la grieta es un `path` muestreado en N puntos; el dedo debe pasar a ≤ 10 px de cada punto, en orden; ≥ 90 % → curar con UV manteniendo 3 s. En mineral o zafiro, el juego explica que se reemplaza.
- **Prensa:** mantener sube la presión; soltar en la zona verde (60–80 %).
- **Desmagnetizar:** alejar el reloj del aparato con velocidad bajo umbral; brújula de referencia.
- **Lubricar:** puntos = `rubies` de los puentes + puntos especiales; aceites: fino de tren, de paletas, grasa de muelle y remontoir, grasa ligera de rotor.
- **Desarmado:** secuencia inversa del nivel; desatornillar exige gesto; «desarmado rápido» después de la primera vez.

## 16. Economía

```text
pago = pago_base × multEstrellas × (1 − 0,05·pistas) × (1 − 0,01·errores) − 0,1·pago_base·díasAtraso
pago = max(pago, 0,5 × pago_base); propina ≤ 15 % con 3 estrellas
reputación += nivel.reputacion × estrellas / 3
desbloqueo(nivel) = nivelAnterior entregado && herramientas_requeridas ⊆ herramientas
```

Formato de dinero: `$` + separador de miles `.` sin decimales (`$45.000`).

## 17. Audio (recetas Web Audio)

| Evento | Receta |
|---|---|
| Tic / tac | Ruido blanco 8 ms → pasa-banda Q 8 a 3,2 kHz (tic) / 2,6 kHz (tac) → envolvente exponencial 30 ms |
| Encaje | Senoidales 2.400 Hz + 3.700 Hz, 120 ms, más clic de ruido de 5 ms |
| Atornillar | Clic de 2 kHz cada 30°; al apretar, doble clic + vibración 15 ms |
| Error | Cuadrada 180 Hz → pasa-bajos 900 Hz, 140 ms, volumen bajo |
| Cuerda | Clic de trinquete cada 30° |
| Tren desbocado | Diente de sierra 90 Hz + ruido, 1,5 s, con caída de frecuencia |
| Cobro | Senoidales 1.320 y 1.980 Hz separadas 60 ms |
| Voltear | Ruido con barrido de filtro 400 → 2.000 Hz, 300 ms |
| Frotar / pulir | Ruido pasa-banda con volumen proporcional a la velocidad del dedo |
| Ultrasonido | Zumbido de 38 Hz + agudo de 12 kHz muy bajo |

- Crear o reanudar el `AudioContext` en el primer `pointerdown` (requisito de iOS).
- Buses de volumen: efectos, tic-tac y ambiente.
- Vibración con `navigator.vibrate` solo si existe (iOS no la tiene).

## 18. Guardado

```js
{ v: 1, dinero, reputacion, dia, dificultad,
  herramientas: ['...'], repuestos: { id: cantidad },
  niveles: { id: { estado, estrellas, mejorTiempo } },
  encargo: { nivelId, fase, vista, piezas: { id: { estado, x, y, rot, espejo, progresoTornillo } },
             pistas: { fichas, acumulado, usadas }, errores, tiempo, defectosPendientes: [] },
  coleccion: [], ajustes: { sonido, ticTac, ambiente, vibracion, zurdo, texto, reducirMovimiento, snap15 } }
```

Autoguardado cada 15 s y en `visibilitychange` oculto. Exportar o importar como texto Base64 desde Ajustes. Si `v` no coincide, migrar o reiniciar con aviso.

## 19. Rendimiento y compatibilidad

- Objetivo: 60 fps en gama media (Android de 2021 en adelante, iPhone 11 en adelante).
- Menos de 2.500 nodos SVG en escena; caché de `path` por pieza; actualizar solo `transform`; `will-change: transform` en la pieza arrastrada.
- Sin `feGaussianBlur` en elementos animados; sombras como elipses translúcidas.
- Probar en Chrome Android, Safari iOS y Chrome de escritorio con emulación táctil.

## 20. Criterios de aceptación

1. El N01 se completa de principio a fin solo con un dedo en una pantalla de 375 × 667.
2. Ninguna pieza puede quedar fuera de la vista, bajo el HUD o inalcanzable, ni siquiera al soltarla en el borde o al girar el teléfono.
3. Las piezas grandes (puentes, esfera, rotor, caja) se achican al acercarse al borde y recuperan su tamaño al alejarse.
4. Con pinzas, cada toque mueve la pieza exactamente el paso configurado hacia el punto tocado; mantener la mueve de forma continua.
5. Rotación con dos dedos y con botones de 15°; el espejo se anima y cambia la cara visible.
6. Cada tornillo pide sus `giros`; el de la rueda de corona del N01 solo se aprieta en sentido antihorario.
7. Una pieza de un paso futuro no encaja y explica por qué; las del mismo paso entran en cualquier orden.
8. «Ver armado» muestra ambos lados durante `memorice_s` y luego reparte las piezas.
9. A los 5:00 de juego activo hay una pista; con la app en segundo plano el contador no avanza.
10. Con el N01 completo y cuerda, suenan 5 golpes por segundo y el volante oscila; sin el áncora aparece «Tren desbocado»; sin el cañón de minutos, «Agujas detenidas».
11. Voltear alterna frente y reverso con animación; las piezas del otro lado no se dibujan.
12. La lista muestra todas las piezas con su estado; tocar una la trae junto al reloj y la selecciona.
13. La ficha de cada pieza muestra nombre, función, material y qué pasa si falta.
14. En iOS los sonidos funcionan después del primer toque.
15. Al recargar la página se conserva el progreso (incluido el encargo a medias).
16. Sin errores en la consola; con `sw.js` publicado, abre sin conexión después de la primera visita.

## 21. Repositorio y despliegue

```text
/
├── index.html                 ← juego (exportado desde Claude Design)
├── manifest.webmanifest
├── sw.js
├── icons/                     ← icon-192.png, icon-512.png, icon-maskable-512.png, apple-touch-icon.png, icon.svg
├── data/                      ← catalogo_base.json, niveles/*.json, catalogo_completo.json
├── docs/                      ← GDD, especificación, prompts por fases
├── tools/build_catalogo.py    ← regenera data/ (python3 tools/build_catalogo.py data)
├── .nojekyll
└── README.md
```

GitHub Pages: *Settings → Pages → Deploy from a branch → main → / (root)*. URL: `https://USUARIO.github.io/REPO/`.
