# Maestro Relojero — Documento de diseño del juego (GDD) v1.0

> Fuente de verdad de datos: `data/catalogo_base.json` y `data/niveles/*.json`.
> Cómo implementarlo: `docs/02_Especificacion_Tecnica.md`.

## 0. Ficha rápida

| Campo | Valor |
|---|---|
| Título provisional | **Maestro Relojero** |
| Género | Simulador de restauración relojera + puzle de armado en orden exacto |
| Plataforma | Navegador del celular (PWA publicada en GitHub Pages); también escritorio |
| Orientación | Vertical prioritaria; horizontal soportada |
| Sesión típica | 10–35 min por encargo, con guardado automático para retomar |
| Idioma | Español neutro con terminología relojera |
| Referencia de género | Simuladores de restauración de PC como *Watch Restoration* (Steam) |
| Monetización | Ninguna (proyecto personal) |

## 1. Visión y pilares

Soy relojero en un taller. Recibo relojes reales de distintas épocas —un reloj de bolsillo de escuela, un cuarzo olvidado, un inglés del siglo XVIII, un ferroviario americano, automáticos modernos, un tourbillon y cronógrafos legendarios—, los diagnostico, los desarmo, los limpio, los reparo y los vuelvo a armar pieza por pieza, en el orden correcto, hasta que vuelven a latir.

1. **Autenticidad.** Calibres y tipos históricos reales, nombres y funciones correctos, secuencias de armado lógicas y síntomas verosímiles cuando falta algo.
2. **Precisión táctil.** El celular es el banco de trabajo: mover, rotar, dar vuelta, tomar con pinzas, atornillar, voltear el reloj.
3. **Progresión de oficio.** De 29 piezas a 77; cada herramienta nueva cambia lo que puedo hacer.
4. **Calma y satisfacción.** El tic-tac a la frecuencia real, el brillo del metal pulido, el clic de un tornillo que asienta.

## 2. Bucle principal

```
Encargo → Diagnóstico → Desarmado → Limpieza y reparación → Armado (puzle) →
Prueba de marcha y regulación → Encajado → Entrega y cobro → Tienda → nuevo encargo
```

| Fase del encargo | Qué hace el jugador | Fase de desarrollo |
|---|---|---|
| Recepción | Lee la ficha del cliente, el reloj, el calibre y el plazo | 1 |
| Diagnóstico | Prueba la marcha, mira con lupa, anota defectos | 2 |
| Desarmado | Retira piezas en orden inverso (versión rápida opcional) | 2 |
| Limpieza y reparación | Mini-juegos: limpiar, pulir, sellar grietas, cambiar piezas… | 2 |
| **Armado** | **Puzle principal: piezas en orden exacto** | **1** |
| Prueba y regulación | Da cuerda, escucha, usa el cronocomparador, regula | 1 (básica) · 4 (completa) |
| Encajado | Caja, corona, rotor, junta y fondo (son pasos del catálogo) | 1 |
| Entrega | Pago, propina, reputación, estrellas, tarjeta para la vitrina | 1 (básica) · 3 |

## 3. El banco de trabajo (pantalla central)

```
┌──────────────────────────────────────┐
│ $45.000  ★★☆  ⏱ 06:12   💡 04:31  ⚙ │  HUD superior
│ N01 · Unitas 6497 · paso 9/25 · 14/29│
├──────────────────────────────────────┤
│   ◦     ⚙          ◦       ⚙         │
│ ⚙    ╭────────────────╮      ◦       │  MESA (tapete)
│      │   MOVIMIENTO   │   ⚙          │  El reloj en el portamovimientos,
│  ◦   │  (lado visible)│        ◦     │  al centro; las piezas alrededor.
│      ╰────────────────╯   ◦          │
│    ⚙      ◦       ⚙          ◦       │
├──────────────────────────────────────┤
│   [⟲] [⟳] [⇋] [🔩] [ⓘ] [✕]          │  Barra contextual (pieza seleccionada)
│ [Piezas] [Voltear] [Herram.] [Ver armado] [Probar] │  Barra inferior
└──────────────────────────────────────┘
```

- El movimiento ocupa cerca del 72 % del ancho en vertical. Alrededor hay mesa libre para dejar piezas.
- Las piezas que no caben al inicio esperan en la **bandeja** (la lista de piezas).
- **Ordenar mesa** reparte las piezas en un anillo ordenado alrededor del reloj.
- **Lupa:** pellizco sobre mesa vacía o botón; el máximo depende de la lupa comprada (×1,5 / ×2,5 / ×4).

## 4. Controles

| Gesto o botón | Acción |
|---|---|
| Tocar una pieza | Seleccionarla (halo dorado) y mostrar la barra contextual |
| Arrastrar con un dedo | Mover la pieza; mientras se arrastra va 48 px por encima del dedo para que se vea |
| Girar con dos dedos sobre la pieza, o ⟲ ⟳ | Rotar (botones en pasos de 15°; mantener repite) |
| ⇋ Espejo | Dar vuelta la pieza (cara A / cara B) |
| Pinzas (en Herramientas) | Con una pieza seleccionada, cada toque en la pantalla la mueve un paso fino hacia el punto tocado; mantener la mueve lento y continuo. Hay cruceta opcional |
| 🔩 Destornillador | Sobre un tornillo colocado: giro circular horario aprieta, antihorario afloja. La rosca izquierda va al revés |
| Mantener 0,5 s o ⓘ | Ficha: nombre, función, material y qué pasa si falta |
| Tocar dos veces el mismo punto | Si hay piezas encimadas, selecciona la de abajo |
| Piezas | Hoja inferior con todas las piezas, su estado y filtros; tocar una la trae junto al reloj |
| Voltear | Cambiar entre frente (esfera) y reverso (puentes) con animación |
| Ver armado | Vista de memoria del reloj completo |
| Probar | Dar cuerda y echarlo a andar |
| ✕ Retirar | Sacar una pieza ya colocada del paso actual para corregir |

Cada gesto tiene alternativa por botón (rotar con botones, pinzas con cruceta, atornillar con botón «mantener»).

## 5. Reglas del puzle de armado

1. **Orden exacto por pasos.** Cada pieza del catálogo tiene un número de `paso`. Las del mismo paso se colocan en cualquier orden entre sí (por ejemplo, los tres tornillos de un puente); los pasos se completan en orden estricto.
2. **Encaje.** Una pieza encaja si es del paso actual, se está viendo su lado (`lado`), está dentro de la tolerancia de posición y, si importa, de rotación, y no está dada vuelta cuando eso importa.
3. **Retroalimentación** (Aprendiz y Oficial): «Casi: gírala», «Está al revés», «Esta va del otro lado: voltea el reloj», «Todavía no: falta algo debajo». En Maestro solo «no encaja».
4. **Tornillos.** Al encajar quedan sueltos; recién cuentan al apretarlos. Tornillos de la misma `variante` son intercambiables entre sus agujeros.
5. **Errores.** Soltar una pieza de otro paso sobre un objetivo suma un error (afecta estrellas y pago). Acercarse sin soltar no castiga.
6. **Resortes bajo tensión** (`pinzas: true`). En Maestro, si se arrastran sin pinzas pueden saltar: vuelan a un punto visible de la mesa con un «tink». Nunca desaparecen.
7. **Alineación de pivotes** (desde N06, Oficial y Maestro). Al poner un puente sobre varias ruedas, sus pivotes aparecen en rojo; hay que tocarlos con pinzas hasta que queden verdes antes de atornillar. En Maestro, atornillar con un pivote rojo lo quiebra y obliga a comprar repuesto.
8. **Preensamblado.** Lo listado en `preensamblado` ya viene armado en la platina.
9. **Submódulo.** Piezas con `modulo` (jaula del tourbillon) se arman con zoom automático sobre su zona.

## 6. Vista de memoria («Ver armado», estilo memorice)

- Al empezar el armado se muestra el reloj completo: primero el reverso y luego el frente, durante `memorice_s` del nivel (10 s en N01 → 5 s en N12). En N01–N02 y en Aprendiz se ven los nombres.
- Después, las piezas «explotan» suavemente hacia la mesa y la bandeja.
- El botón **Ver armado** repite la vista: 1 uso gratis por nivel; luego cuesta $2.000 o una pista. Enfriamiento de 60 s.
- El **Manual técnico** suma 3 s.

## 7. Pistas cada 5 minutos

- Se gana una pista cada **5 minutos de juego activo** (se pausa en menús y con la app en segundo plano). Máximo acumulable: 1 (configurable).
- El botón muestra un anillo de progreso y la cuenta regresiva.
- Al usarla, la pieza siguiente pulsa con halo dorado, su «fantasma» aparece en el lugar y la orientación exactos durante 6 s y se muestra su nombre. Si está en la bandeja se resalta en la lista; si hay que voltear, primero lo indica.
- Cada pista usada descuenta 5 % del pago.

## 8. Prueba de marcha y diagnóstico

- **Dar cuerda:** giro circular sobre la corona o botón mantener; un clic de trinquete cada 30° y una barra de reserva. En automáticos también se puede «agitar» (botón).
- **Simulación:** con lo que está colocado y los defectos pendientes se calcula el síntoma principal (el `efecto` de mayor prioridad) y los secundarios.
- **Si todo está bien:** el volante oscila, la rueda de escape avanza a saltos, las ruedas giran a su ritmo y suena el tic-tac a la frecuencia real (18.000 A/h = 5 golpes por segundo; 21.600 = 6; 28.800 = 8; 36.000 = 10). En cuarzo, el segundero salta una vez por segundo.
- **Si algo falla:** se anima el síntoma (tren desbocado con zumbido, volante quieto, agujas detenidas, fecha a medias…) y el panel Diagnóstico describe lo observado sin revelar la pieza, salvo que se use una pista.
- **Cronocomparador** (Fase 4): marcha en s/día, amplitud en grados, error de ritmo en ms y gráfico de puntos. Se regula con la raqueta, la raqueta micrométrica o las tuercas Microstella (siempre por pares opuestos).

## 9. Reparación (mini-juegos)

| Operación | Herramienta | Gesto | Éxito | Error típico |
|---|---|---|---|---|
| Limpiar | Pera de aire, pincel | Soplar/frotar sobre la capa de suciedad | ≥ 95 % limpio | Quedan restos: amplitud baja |
| Limpieza por ultrasonido | Limpiadora | Llevar piezas sucias a la cesta e iniciar ciclos | Todas limpias | Piezas olvidadas siguen sucias |
| Lubricar | Aceiteras | Elegir aceite y tocar cada punto marcado con gota justa | Gota en zona verde | Exceso (mancha) o falta (seco) |
| Pulir | Paño, pasta, motor | Frotar sobre las rayas | Rayas < 5 % | Sobrepulir redondea aristas (baja el valor) |
| **Sellar grieta de cristal** | Resina UV | Trazar la grieta con la resina y curar con la lámpara 3 s | Trazo ≥ 90 % | Fuera del trazo: mancha. Solo acrílico; en mineral y zafiro el juego explica que se reemplaza |
| Reemplazar cristal | Pie de metro, prensa | Medir, elegir el diámetro, presionar en zona verde | Medida y presión correctas | Presión excesiva rompe el repuesto |
| Cambiar pila | Probador, cuchilla | Abrir, soltar brida, poner la nueva con «+» hacia arriba | Polaridad correcta | Invertida: síntoma «pila invertida» |
| Limpiar contactos | Lápiz de fibra | Frotar | Contactos limpios | — |
| Medir bobina | Multímetro | Tocar terminales | Lectura normal | Bobina cortada: reemplazar |
| Desmagnetizar | Desmagnetizador | Acercar y alejar lento | Brújula quieta | Alejar rápido deja magnetismo |
| Reemplazar pieza | Repuesto de la tienda | Detectar con lupa, desmontar, montar | Pieza nueva colocada | Falta de repuesto: comprar |
| Cambiar junta y probar hermeticidad | Probador | Colocar junta; ciclo de presión | Pasa la prueba | Junta vieja: falla |
| Cambiar correa | Herramienta de pasadores | Comprimir pasador y soltar | Correa puesta | — |
| Ajustar excéntrico | Destornillador | Girar el tornillo excéntrico hasta la marca | Embrague engrana | Muy profundo o muy flojo |
| Limpiar cadena del caracol | Pera de aire, aceite fino | Frotar eslabones | Sin óxido | — |
| Informar al cliente | — | Elegir «no intervenir» o «intentar» ante un pelo en el esmalte | Informar suma reputación | Intentarlo puede empeorarlo |

## 10. Progresión y economía

- **Moneda:** pesos chilenos (CLP), formato `$45.000`. Dinero inicial: $20.000.
- **Pago:** `pago_base × estrellas × (1 − 0,05 × pistas) × (1 − 0,01 × errores) − atraso` (mínimo 50 % del base; propina de hasta 15 % con 3 estrellas). Estrellas: ×1,0 / ×1,1 / ×1,25.
- **Estrellas:** 3 = sin pistas extra, ≤ 3 errores y bajo el tiempo objetivo; 2 = ≤ 2 pistas y ≤ 8 errores; 1 = entregado funcionando.
- **Reputación:** suma por encargo; desbloquea clientes y relojes más exigentes.
- **Desbloqueo de niveles:** nivel anterior entregado + herramientas exigidas compradas.
- **Trabajos rápidos** repetibles (pila, correa, pulido, desmagnetizado, hermeticidad) para juntar dinero si falta.
- **Vitrina:** cada reloj entregado deja una tarjeta con su ficha, la foto esquemática y la frase del cliente.
- **Enciclopedia:** piezas aprendidas (nombre, función, material) y fichas de calibres con historia y «¿Sabías que?».

### 10.1 Los 12 encargos (de menos a más)

| N.º | Encargo | Calibre (casa) | Época | Frecuencia | Piezas / pasos | Mecánicas nuevas | Defectos a reparar | Herramientas que exige | Pago base |
|---|---|---|---|---|---|---|---|---|---|
| 1 | El reloj de la escuela | Unitas 6497 (Unitas, Suiza) | 1950 | 18.000 A/h | 29 / 25 | mover, rotar, voltear, atornillar, rosca izquierda, lista, info, memorice, pistas, probar marcha | movimiento sucio | iniciales | $30.000 |
| 2 | El cuarzo del cajón | Miyota 2035 (Citizen, Japón) | Cuarzo actual | 32.768 Hz | 34 / 33 | espejo, polaridad de pila, encajado, fondo a presión | pila agotada, contactos sulfatados, cristal mineral trizado | Cuchilla abre-fondos | $40.000 |
| 3 | El inglés del remate | Catalina y caracol (taller londinense) | c. 1780 | ≈ 17.280 A/h | 36 / 32 | pasadores, cadena del caracol, llave de cuerda, esfera de esmalte | cadena oxidada, pelo en el esmalte, cristal de vidrio roto | Llave de cuerda | $70.000 |
| 4 | La hora del ferrocarril | Hamilton 992B (EE. UU.) | 1940 | 18.000 A/h | 40 / 36 | resortes con pinzas, puesta en hora por palanca, raqueta micrométrica, fondo enroscado | espiral magnetizado, muelle real roto, caja rayada | Abridor de fondos | $85.000 |
| 5 | La buzo del fin de semana | Seiko NH35 (Japón) | Década de 2010 | 21.600 A/h | 43 / 39 | automático, Magic Lever, calendario, rotor al encajar | junta reseca, rotor ruidoso, bisel rayado | Lupa ×5 | $95.000 |
| 6 | El automático de todos los días | ETA 2824-2 (Suiza) | 1971 / 1982 | 28.800 A/h | 53 / 44 | ruedas inversoras, corrector de fecha, bridas de encajado, alineación de pivotes | movimiento sucio, salteador fatigado, desregulado | Pinzas antimagnéticas | $120.000 |
| 7 | Ochenta horas de vuelo | Hamilton H-40 (Suiza) | Actual | 21.600 A/h | 56 / 47 | día y fecha, reserva de 80 h | espiral magnetizado, correa gastada, zafiro astillado | Desmagnetizador | $150.000 |
| 8 | Presión de las profundidades | Rolex 3135 (Ginebra) | 1988 | 28.800 A/h | 58 / 47 | volante libre con Microstella, puente de doble apoyo, fecha instantánea, tornillos de pie de esfera, cronómetro | lubricación agotada, fuera de ritmo, junta reseca, caja rayada | Cronocomparador, llave de fondos herméticos, llave Microstella | $260.000 |
| 9 | El torbellino | Tourbillon de un minuto (invento de Breguet) | 1801 · actual | 21.600 A/h | 63 / 50 | jaula de tourbillon, lupa ×10, submódulo | eje de volante roto, movimiento sucio, desregulado | Lupa ×10, kit de tourbillon | $380.000 |
| 10 | Contra el reloj | Valjoux 7750 (Suiza) | 1974 | 28.800 A/h | 65 / 58 | cronógrafo de leva, piñón oscilante, contadores | resorte de martillos fatigado, rotor ruidoso, movimiento sucio | Saca-agujas, colocador de agujas | $300.000 |
| 11 | Un cronógrafo para la Luna | Omega 321 / Lemania 2310 (Suiza) | 1942 | 18.000 A/h | 70 / 65 | rueda de pilares, embrague horizontal, tornillo excéntrico, cristal acrílico aparte | acrílico rayado, microgrieta, lubricación agotada, embrague desajustado | Prensa de cristales | $420.000 |
| 12 | El primero | Zenith El Primero 3019 PHC (Suiza) | 1969 | 36.000 A/h | 77 / 68 | alta frecuencia de 5 Hz, cronógrafo automático integrado | sucio, lubricación agotada, desregulado, caja rayada, junta reseca | Aceiteras | $520.000 |

### 10.2 Tienda de herramientas

| Herramienta | Precio | Qué permite |
|---|---|---|
| Portamovimientos, destornilladores (5 tamaños), pinzas de latón, lupa ×3, pera de aire, paño de pulir | Inicial | Lo básico del banco |
| Llave de cuerda antigua | $5.000 | Relojes de llave del siglo XVIII |
| Cuchilla abre-fondos | $8.000 | Fondos a presión |
| Pasta para pulir acrílico | $8.000 | Pulido de acrílico ×2 más rápido |
| Lápiz de fibra de vidrio | $6.000 | Limpiar contactos de cuarzo |
| Herramienta de pasadores | $9.000 | Correas y brazaletes |
| Probador de pilas | $12.000 | Medir la pila |
| Pie de metro digital | $15.000 | Medir cristales |
| Saca-agujas / colocador de agujas | $18.000 / $22.000 | Agujas sin marcar la esfera; necesarios en cronógrafos |
| Lupa ×5 / ×10 | $25.000 / $55.000 | Zoom ×2,5 / ×4 |
| Multímetro | $25.000 | Bobina y consumo del cuarzo |
| Resina UV y lámpara | $30.000 | Sellar microgrietas en acrílico |
| Llave Microstella | $30.000 | Regular volantes libres |
| Abridor de fondos enroscados | $35.000 | Fondos con muescas |
| Desmagnetizador | $40.000 | Quitar magnetismo |
| Manual técnico | $40.000 | +3 s de vista de armado |
| Pinzas antimagnéticas finas | $45.000 | Paso fino y alineación de pivotes |
| Llave de fondos herméticos | $45.000 | Fondos estriados de buceo |
| Aceiteras y 4 aceites | $50.000 | Lubricación correcta |
| Destornilladores profesionales | $60.000 | +2 tamaños, 30 % más rápidos |
| Prensa de cristales | $60.000 | Colocar cristales |
| Motor de pulido | $110.000 | Pulido de acero ×3 |
| Limpiadora por ultrasonido | $140.000 | Limpieza en lote |
| Kit de tourbillon | $180.000 | Armar la jaula |
| Cronocomparador | $220.000 | Medir marcha, amplitud y error de ritmo |
| Probador de hermeticidad | $250.000 | Pruebas de presión |

Repuestos (muelle real, eje de volante, cristales, juntas, coronas, pilas, tornillos, salteadores, bobinas, correas, resortes y agujas) se compran en la misma tienda con los precios del catálogo.

## 11. Clientes y tono

Clientes ficticios con historias breves y cálidas, ambientadas en Chile (Santiago, Valparaíso, San Bernardo, Quintero, Antofagasta, Talcahuano, Concepción, Atacama, Punta Arenas). Tono cercano y respetuoso; nunca personas reales. El cliente reacciona al entregar según estrellas y plazo.

## 12. Dirección de arte

- **Mesa:** tapete verde oscuro (#1F3B33) con textura sutil y luz cálida cenital; el portamovimientos en el centro.
- **Materiales:** latón dorado, acero rodiado, acero azulado al calor (tornillos), rubíes rojos con brillo, oro para el puente calado del siglo XVIII, esmalte blanco cálido para esferas antiguas.
- **Decoraciones:** perlage en la platina, Côtes de Genève en puentes, soleil en rochete y rueda de corona, biselado claro de 1 px en los bordes.
- **Tipografía:** títulos con serif clásica; interfaz con sans legible de al menos 14 px; números tabulares para dinero y tiempos.
- **Animaciones:** 150–300 ms; al encajar, la pieza se asienta (escala 1,04 → 1) con un destello corto.
- **Iconos:** de línea, propios.
- **Regla de marcas:** las marcas y calibres reales aparecen solo como texto en fichas e historias. No se dibujan logotipos ni nombres de marca en esferas, rotores o puentes, ni se copian diseños icónicos de cajas o esferas. En Créditos: «Marcas mencionadas con fines descriptivos; juego no afiliado».

## 13. Audio

| Evento | Sonido (sintetizado) |
|---|---|
| Tic-tac | Golpes cortos y metálicos alternados (tic más agudo, tac más grave) a la frecuencia del calibre |
| Tomar pieza | Clic metálico suave |
| Encaje correcto | «Ping» limpio con un clic de asiento |
| Error | Golpe grave y breve, a bajo volumen |
| Atornillar | Clic cada 30° y doble clic final al quedar apretado |
| Dar cuerda | Trinquete por cada 30° |
| Tren desbocado | Zumbido que baja de tono y se apaga |
| Voltear | Silbido corto |
| Pulir, frotar | Ruido suave proporcional a la velocidad del dedo |
| Ultrasonido | Zumbido grave con un agudo muy bajo |
| Cobro | Dos campanitas |
| Ambiente (opcional) | Reloj de pared lejano |

Controles de volumen separados (efectos, tic-tac, ambiente) y vibración corta donde el equipo la soporte.

## 14. Pantallas

1. **Inicio:** Continuar, Nueva partida, Ajustes, Créditos.
2. **Taller (hub):** mostrador con encargos (disponibles y con candado, mostrando qué falta), acceso a Tienda, Vitrina, Enciclopedia y Trabajos rápidos; saldo y reputación.
3. **Ficha del encargo:** cliente, pedido, plazo, reloj, calibre, ficha técnica, historia y «¿Sabías que?».
4. **Banco de trabajo:** descrito arriba.
5. **Reparación:** cada mini-juego en una vista enfocada del mismo banco.
6. **Resultado:** estrellas, tiempo, pistas, errores, pago, propina, reputación y frase del cliente.
7. **Tienda, Vitrina, Enciclopedia, Ajustes** (dificultad, sonido, vibración, zurdo, tamaño de texto, reducir movimiento, exportar/importar partida, reiniciar).

## 15. Dificultad y accesibilidad

- **Aprendiz:** tolerancias amplias, nombres en la vista de memoria, ayudas de orientación.
- **Oficial (por defecto):** tolerancias medias y ayudas.
- **Maestro:** tolerancias finas, sin ayudas de orientación; tornillos que se pasan de rosca, resortes que saltan y pivotes que se quiebran.
- Modo zurdo (barra contextual al otro lado), texto grande, alto contraste, reducir movimiento y vibración apagable.
- Nada depende solo del color: los estados llevan ícono o texto.

## 16. Guardado

Automático cada 15 s y al pasar a segundo plano, en `localStorage` (`relojero_save_v1`): dinero, reputación, día, herramientas, repuestos, niveles con estrellas y mejor tiempo, encargo en curso (posición de cada pieza, pistas, errores, tiempo) y ajustes. Exportar e importar la partida como texto para cambiar de equipo.

## 17. Fuera de alcance de la versión 1

Multijugador, cuentas, nube, compras dentro de la app y relojes inteligentes.

## 18. Glosario breve

| Término | Significado |
|---|---|
| Platina | Placa base del movimiento |
| Puente | Pieza atornillada que sostiene ruedas por arriba |
| Barrilete / muelle real | Tambor con el resorte que da la energía |
| Rochete | Rueda de trinquete sobre el eje del barrilete |
| Tren de rodaje | Rueda de centro, tercera, cuarta y escape |
| Áncora / volante / espiral | El escape y el órgano regulador |
| Remontoir | Mecanismo de cuerda y puesta en hora (tija, tirete, báscula, piñones) |
| Minutería | Cañón de minutos, rueda de minutos y rueda de horas |
| A/h | Alternancias por hora (18.000 A/h = 2,5 Hz) |
| Lépine | Reloj de bolsillo con la corona a las 12 y el segundero a las 6 |
| Microstella | Tuercas en el aro del volante libre para regular |
| Rueda de pilares / leva | Mandos del cronógrafo |
| Tourbillon | Jaula giratoria con escape y volante |
