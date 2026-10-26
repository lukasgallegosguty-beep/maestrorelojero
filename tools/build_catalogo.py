#!/usr/bin/env python3
"""Genera los archivos de data/ (catalogo_base.json, niveles/*.json y catalogo_completo.json) para "Maestro Relojero".
Uso (desde la raíz del repositorio): python3 tools/build_catalogo.py data
Convenciones geométricas (ver 02_Especificacion_Tecnica.md):
  - Unidades: la platina mide radio 100. Origen = centro del movimiento.
  - Eje y hacia abajo (como SVG). Ángulos en grados, sentido horario desde las 12.
  - Cada pieza declara su 'lado' ('reverso' = lado puentes, 'frente' = lado esfera).
    Las coordenadas se expresan tal como se ve ESE lado. Un eje compartido aparece en
    el otro lado con x espejada (x -> -x).
"""
import json, math, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"

# ------------------------------------------------------------------ geometría
def pol(d, th):
    r = math.radians(th)
    return (d * math.sin(r), -d * math.cos(r))

def ang(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return (math.degrees(math.atan2(dx, -dy)) + 360) % 360

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def r1(v):
    v = round(v, 1)
    return 0.0 if v == 0 else v

def mir(p):
    return (-p[0], p[1])

def circle_pts(c, r, n=18):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]

def hull(points):
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in points))
    if len(pts) <= 2:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]

def decimate(poly, max_n=22):
    while len(poly) > max_n:
        poly = poly[::2]
    return poly

def centroid(poly):
    a = cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    if abs(a) < 1e-9:
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))

def inside(p, poly):
    x, y = p; ins = False; n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        if ((y0 > y) != (y1 > y)) and (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0):
            ins = not ins
    return ins

def choose_screws(poly, avoid, k, inset=7.5, min_avoid=12.0, rmax=93.0):
    c = centroid(poly)
    cands = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        steps = max(1, int(dist(a, b) / 2.5))
        for s in range(steps):
            t = s / steps
            x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
            dx, dy = c[0] - x, c[1] - y; d = math.hypot(dx, dy) or 1
            p = (x + dx / d * inset, y + dy / d * inset)
            if inside(p, poly) and math.hypot(*p) <= rmax and all(dist(p, q) >= min_avoid for q in avoid):
                cands.append(p)
    if len(cands) < k:  # relaja la restricción si el puente es muy chico
        return choose_screws(poly, avoid, k, inset, min_avoid - 3, rmax) if min_avoid > 6 else [c] * k
    chosen = [max(cands, key=lambda p: dist(p, c))]
    while len(chosen) < k:
        chosen.append(max(cands, key=lambda p: min(dist(p, q) for q in chosen)))
    return chosen

def ring_sector(r_out, r_in, a0, a1, n=12):
    pts = [pol(r_out, a0 + (a1 - a0) * i / n) for i in range(n + 1)]
    pts += [pol(r_in, a1 - (a1 - a0) * i / n) for i in range(n + 1)]
    return pts

def loc(pts, c):
    return [[r1(x - c[0]), r1(y - c[1])] for x, y in pts]

# ------------------------------------------------------------------ efectos (síntomas)
EFECTOS = {
    "SIN_ENERGIA":           (1, "Sin energía", "No llega energía al tren de ruedas: el reloj no arranca."),
    "NO_ARRANCA":            (1, "No arranca", "El reloj no marcha aunque tenga cuerda: el tren está cortado o bloqueado."),
    "TREN_DESBOCADO":        (1, "Tren desbocado", "Al dar cuerda, las ruedas giran sin control y el muelle se descarga en segundos con un zumbido."),
    "POLARIDAD_INVERTIDA":   (1, "Pila invertida", "La pila está al revés: no hay contacto correcto."),
    "SIN_CADENA":            (1, "Sin transmisión", "El caracol no recibe la fuerza del muelle: falta la cadena."),
    "NO_DA_CUERDA":          (2, "No da cuerda", "La corona gira en vacío: el muelle real no recibe cuerda."),
    "NO_RETIENE_CUERDA":     (2, "No retiene la cuerda", "Se puede dar cuerda, pero el muelle se suelta de inmediato."),
    "VOLANTE_QUIETO":        (2, "El volante no oscila", "El órgano regulador falta, no tiene apoyo o está bloqueado."),
    "MOTOR_NO_GIRA":         (2, "El motor no gira", "Llegan pulsos eléctricos, pero el rotor del motor no avanza."),
    "JAULA_QUIETA":          (2, "Jaula detenida", "La jaula del tourbillon no gira."),
    "MARCHA_IRREGULAR":      (3, "Marcha irregular", "Se detiene en algunas posiciones o con golpes suaves: algo quedó suelto."),
    "AGUJAS_QUIETAS":        (3, "Agujas detenidas", "El mecanismo late, pero las agujas no avanzan."),
    "HORARIO_QUIETO":        (4, "Horario detenido", "El minutero avanza, pero el horario no lo acompaña."),
    "NO_PONE_HORA":          (4, "No ajusta la hora", "Al tirar la corona (o la palanca) no se pueden mover las agujas."),
    "CORONA_SIN_POSICIONES": (4, "Corona sin posiciones", "La corona no queda en sus posiciones o se sale."),
    "SIN_AUTOCUERDA":        (4, "No se da cuerda solo", "El rotor gira, pero no carga el muelle real."),
    "CRONO_NO_ARRANCA":      (4, "El cronógrafo no arranca", "Al pulsar, el segundero del cronógrafo no se mueve."),
    "CRONO_NO_SE_DETIENE":   (4, "El cronógrafo no se detiene", "El cronógrafo no frena o no queda en su posición al pulsar."),
    "AMPLITUD_BAJA":         (5, "Amplitud baja", "El volante oscila con poca fuerza: atrasa y se detiene antes de tiempo."),
    "ADELANTA_MUCHO":        (5, "Adelanta muchísimo", "Gana minutos por día: las espiras del espiral se pegan (magnetismo)."),
    "FECHA_NO_CAMBIA":       (5, "La fecha no cambia", "El disco de fechas no avanza a medianoche."),
    "FECHA_DESALINEADA":     (5, "Indicación desalineada", "El número o el día queda a medio camino en la ventanilla."),
    "DIA_NO_CAMBIA":         (5, "El día no cambia", "El disco de días no avanza."),
    "CRONO_NO_VUELVE_A_CERO": (5, "No vuelve a cero", "Las agujas del cronógrafo no regresan a cero."),
    "CONTADOR_QUIETO":       (5, "Contador detenido", "El contador de minutos u horas del cronógrafo no avanza."),
    "MOVIMIENTO_SUELTO":     (5, "Movimiento suelto", "El movimiento baila dentro de la caja."),
    "DESREGULADO":           (6, "Desregulado", "Marcha, pero fuera de la tolerancia diaria."),
    "FUERA_DE_RITMO":        (6, "Fuera de ritmo", "El tic y el tac suenan desparejos (error de ritmo alto)."),
    "ROTOR_RUIDOSO":         (6, "Rotor ruidoso", "El rotor roza o raspa al girar."),
    "NO_HERMETICO":          (6, "No es hermético", "Falla la prueba de hermeticidad: puede entrar humedad."),
    "SIN_TOPE":              (6, "Riesgo de sobrecuerda", "Nada detiene la cuerda al llegar al final: la cadena puede cortarse."),
    "SIN_CORRECCION":        (7, "Sin corrección rápida", "No se puede corregir la fecha desde la corona."),
    "SIN_PROTECCION":        (7, "Sin protección", "Esfera y movimiento quedan expuestos a polvo y golpes."),
    "INCOMPLETO":            (7, "Incompleto", "No afecta la marcha, pero el reloj no está terminado."),
}

# ------------------------------------------------------------------ tipos de pieza
# clave: (nombre, categoría, función, efecto_si_falta, texto_si_falta, material)
T = {}
def tipo(k, nombre, cat, funcion, efecto, texto, material="", pinzas=False):
    assert efecto in EFECTOS, (k, efecto)
    T[k] = {"nombre": nombre, "categoria": cat, "funcion": funcion,
            "si_falta": {"efecto": efecto, "texto": texto}}
    if material: T[k]["material"] = material
    if pinzas: T[k]["requierePinzas"] = True

# Estructura
tipo("platina", "Platina", "estructura", "Placa base del movimiento: lleva los rubíes inferiores y los asientos de casi todas las piezas.", "NO_ARRANCA", "Sin platina no hay movimiento.", "Latón rodiado con perlage")
tipo("puente_barrilete", "Puente de barrilete", "estructura", "Sujeta por arriba el eje del barrilete (y en algunos calibres la rueda de centro); lleva el rochete y la rueda de corona.", "MARCHA_IRREGULAR", "El barrilete queda sin apoyo superior y frena el tren.", "Latón rodiado, Côtes de Genève")
tipo("puente_rodaje", "Puente de rodaje", "estructura", "Sostiene los pivotes superiores de las ruedas del tren para que giren paralelas y con el juego justo.", "MARCHA_IRREGULAR", "Las ruedas del tren bailan y se traban.", "Latón rodiado")
tipo("puente_barrilete_rodaje", "Puente de barrilete y rodaje", "estructura", "Puente único que sujeta el barrilete y las ruedas del tren; típico de calibres fabricados en grandes series.", "MARCHA_IRREGULAR", "Barrilete y ruedas quedan sin apoyo superior.", "Latón niquelado")
tipo("puente_ancora", "Puente del áncora", "estructura", "Sujeta el pivote superior del áncora, la pieza que reparte los impulsos al volante.", "MARCHA_IRREGULAR", "El áncora se inclina: el escape traba o se suelta.", "Latón rodiado")
tipo("puente_volante_doble", "Puente de volante de doble apoyo", "estructura", "Cruza sobre el volante y se atornilla en dos puntos: más estable ante golpes que un puente de un solo brazo.", "VOLANTE_QUIETO", "El volante no tiene apoyo superior.", "Latón rodiado")
tipo("puente_volante_calado", "Puente de volante calado y grabado", "estructura", "En los relojes del siglo XVIII este puente, perforado y grabado a mano, protegía el volante y lucía el arte del grabador.", "VOLANTE_QUIETO", "El volante no tiene apoyo superior.", "Latón dorado al fuego")
tipo("puente_automatico", "Puente del automático", "estructura", "Sostiene las ruedas del mecanismo de carga automática y el eje del rotor.", "SIN_AUTOCUERDA", "Las ruedas del automático quedan sueltas.", "Latón rodiado")
tipo("puente_cronografo", "Puente de cronógrafo", "estructura", "Sujeta la rueda de cronógrafo y los contadores sobre el movimiento base.", "CRONO_NO_ARRANCA", "La rueda de cronógrafo queda sin apoyo.", "Latón rodiado")
tipo("puente_contador_horas", "Puente del contador de horas", "estructura", "Pequeño puente que sostiene la rueda contadora de horas del cronógrafo.", "CONTADOR_QUIETO", "El contador de horas queda sin apoyo.", "Latón rodiado")
tipo("puente_tourbillon", "Puente del tourbillon", "estructura", "Arco que sostiene el pivote superior de la jaula giratoria.", "JAULA_QUIETA", "La jaula no tiene apoyo superior.", "Latón rodiado pulido espejo")
tipo("platina_superior", "Platina superior", "estructura", "En los relojes antiguos de pilares, una segunda placa completa encierra el tren entre ambas platinas.", "MARCHA_IRREGULAR", "El tren queda sin apoyo superior.", "Latón dorado al fuego")
tipo("puente_calendario", "Placa del calendario", "calendario", "Mantiene en su lugar el disco de fechas y sus resortes bajo la esfera.", "FECHA_DESALINEADA", "El disco de fechas se levanta y queda desalineado.", "Acero o latón con perlage")
tipo("tornillo", "Tornillo", "tornilleria", "Fija un puente o pieza. Cada tornillo tiene su largo y su cabeza: cambiarlos de lugar puede dañar roscas o rubíes.", "MARCHA_IRREGULAR", "Una pieza quedó suelta.", "Acero, a menudo azulado al calor")
tipo("tornillo_excentrico", "Tornillo excéntrico", "tornilleria", "Su cabeza descentrada permite ajustar con precisión una profundidad de engrane o un tope al girarlo.", "CRONO_NO_ARRANCA", "El embrague queda sin ajuste y no engrana bien.", "Acero")
tipo("pasador", "Pasador", "tornilleria", "Clavija cónica que fija una platina o la esfera a sus pilares; se usaba antes de que los tornillos fueran comunes.", "MARCHA_IRREGULAR", "La platina o la esfera quedan sueltas.", "Latón o acero")
# Energía
tipo("barrilete", "Barrilete con muelle real", "energia", "Tambor dentado que aloja el muelle real (resorte principal). Al desenrollarse, el muelle lo hace girar y entrega energía al tren.", "SIN_ENERGIA", "No hay fuente de energía.", "Latón; muelle de aleación Nivaflex")
tipo("barrilete_80h", "Barrilete de larga reserva", "energia", "Muelle real más largo y fino que, junto a una frecuencia reducida, permite hasta 80 horas de marcha.", "SIN_ENERGIA", "No hay fuente de energía.", "Latón; muelle de aleación de alto rendimiento")
tipo("barrilete_caracol", "Barrilete (sin dentado)", "energia", "En los relojes de caracol el barrilete no engrana: tira de una cadena enrollada a su alrededor.", "SIN_ENERGIA", "No hay fuente de energía.", "Latón; muelle de acero templado")
tipo("rochete", "Rochete (rueda de trinquete)", "energia", "Rueda montada sobre el eje del barrilete: al dar cuerda gira y tensa el muelle; el trinquete impide que retroceda.", "NO_DA_CUERDA", "La cuerda no llega al muelle real.", "Acero pulido con soleil")
tipo("rueda_corona", "Rueda de corona", "energia", "Transmite el giro de la corona al rochete. Su tornillo suele tener rosca izquierda: se aprieta girando al revés.", "NO_DA_CUERDA", "La corona gira en vacío.", "Acero pulido")
tipo("trinquete", "Trinquete (clic)", "energia", "Uñeta que encaja en los dientes del rochete y evita que el muelle real se descargue de golpe.", "NO_RETIENE_CUERDA", "El muelle se descarga apenas sueltas la corona.", "Acero")
tipo("resorte_trinquete", "Resorte del trinquete", "energia", "Mantiene el trinquete apretado contra el rochete. Está bajo tensión: tómalo con pinzas o saltará.", "NO_RETIENE_CUERDA", "El trinquete no presiona y la cuerda se escapa.", "Acero templado", pinzas=True)
tipo("caracol", "Caracol (fusee) con rueda grande", "energia", "Cono escalonado que compensa la fuerza decreciente del muelle: con el muelle lleno la cadena tira del radio chico y, al agotarse, del grande.", "NO_ARRANCA", "La fuerza del barrilete no llega al tren.", "Latón y acero")
tipo("cadena_caracol", "Cadena del caracol", "energia", "Cadena diminuta de eslabones remachados que une el barrilete con el caracol.", "SIN_CADENA", "El caracol no recibe la fuerza del muelle.", "Acero")
tipo("tope_caracol", "Tope del caracol", "energia", "Palanca que detiene la cuerda cuando la cadena llegó al extremo del caracol.", "SIN_TOPE", "Nada detiene la cuerda al final del recorrido.", "Acero")
tipo("rochete_armado", "Rochete de armado", "energia", "Da al muelle real una tensión inicial fija en los relojes de caracol.", "AMPLITUD_BAJA", "Sin tensión inicial, el reloj se detiene antes de tiempo.", "Acero")
tipo("trinquete_armado", "Trinquete de armado", "energia", "Retiene el rochete de armado en la tensión elegida.", "AMPLITUD_BAJA", "El muelle pierde su tensión inicial.", "Acero")
tipo("resorte_trinquete_armado", "Resorte del trinquete de armado", "energia", "Mantiene el trinquete de armado contra su rochete. Está bajo tensión.", "AMPLITUD_BAJA", "El muelle pierde su tensión inicial.", "Acero templado", pinzas=True)
tipo("pila", "Pila de óxido de plata SR626SW", "cuarzo", "Fuente de energía del cuarzo. La cara con «+» debe quedar hacia arriba.", "SIN_ENERGIA", "No hay pila.", "Óxido de plata")
tipo("brida_pila", "Brida de la pila", "cuarzo", "Lámina elástica que sujeta la pila y cierra el contacto eléctrico.", "SIN_ENERGIA", "La pila no hace contacto.", "Acero niquelado")
# Rodaje
tipo("rueda_centro", "Rueda de centro", "rodaje", "Gira una vez por hora. Recibe la fuerza del barrilete y, del lado de la esfera, lleva el cañón que mueve el minutero.", "NO_ARRANCA", "Se corta el tren: la fuerza del barrilete no llega al escape.", "Latón dorado")
tipo("rueda_central_cuarzo", "Rueda central (2.ª rueda)", "rodaje", "En el cuarzo gira una vez por hora y mueve el minutero.", "AGUJAS_QUIETAS", "El segundero avanza, pero el minutero no.", "Latón")
tipo("tercera_rueda", "Tercera rueda", "rodaje", "Rueda intermedia que multiplica la velocidad entre la rueda de centro y la de segundos.", "NO_ARRANCA", "Se corta el tren.", "Latón dorado")
tipo("cuarta_rueda", "Cuarta rueda (rueda de segundos)", "rodaje", "Da una vuelta por minuto; su eje lleva el segundero pequeño.", "NO_ARRANCA", "Se corta el tren.", "Latón dorado")
tipo("rueda_segundos_central", "Rueda de segundos central", "rodaje", "Cuarta rueda ubicada en el centro: su eje largo pasa por dentro de la rueda de centro y lleva el segundero central.", "NO_ARRANCA", "Se corta el tren.", "Latón dorado")
tipo("quinta_rueda", "Quinta rueda", "rodaje", "En el cuarzo, reduce el giro rápido del motor hacia la rueda de segundos.", "AGUJAS_QUIETAS", "El motor gira, pero las agujas no.", "Latón o polímero")
tipo("rueda_contrapunto", "Rueda de contrapunto", "rodaje", "Rueda con dientes perpendiculares que cambia el plano del giro para mover la rueda catalina.", "NO_ARRANCA", "Se corta el tren.", "Latón")
tipo("rueda_fija_tourbillon", "Rueda fija del tourbillon", "tourbillon", "Rueda inmóvil atornillada al movimiento: el piñón de escape rueda a su alrededor y así la jaula gira.", "JAULA_QUIETA", "La jaula no tiene sobre qué rodar.", "Latón dorado")
# Escape y regulación
tipo("rueda_escape", "Rueda de escape", "escape", "Rueda de dientes en forma de gancho que libera la energía de a poco, diente por diente, a través del áncora.", "TREN_DESBOCADO", "Nada frena el tren.", "Acero templado")
tipo("ancora", "Áncora", "escape", "Horquilla con dos paletas de rubí: bloquea la rueda de escape y da un pequeño impulso al volante en cada oscilación.", "TREN_DESBOCADO", "La rueda de escape gira libre.", "Acero con paletas de rubí")
tipo("rueda_catalina", "Rueda catalina", "escape", "Rueda de escape del escape de paletas (verge): sus dientes de sierra empujan alternadamente las dos paletas de la vara.", "TREN_DESBOCADO", "Nada frena el tren.", "Latón")
tipo("contrapotenza", "Contrapotenza", "escape", "Soporte atornillado que sostiene el pivote exterior de la rueda catalina.", "MARCHA_IRREGULAR", "La rueda catalina queda sin apoyo.", "Latón")
tipo("volante_vara", "Volante con vara de paletas", "regulacion", "En el escape de catalina, el eje del volante (la vara) lleva dos paletas que reciben los empujes de la rueda catalina.", "TREN_DESBOCADO", "La rueda catalina gira libre.", "Acero y latón")
tipo("volante", "Volante con espiral y puente", "regulacion", "El corazón del reloj: oscila a ritmo constante gracias a su espiral. Se monta junto a su puente (coq).", "NO_ARRANCA", "El áncora bloquea el tren: sin volante no hay oscilación.", "Glucydur o níquel; espiral Nivarox")
tipo("volante_libre", "Volante libre con tuercas Microstella", "regulacion", "Volante sin raqueta: se regula girando pares opuestos de tuercas en su aro. El espiral lleva curva terminal Breguet para marchar parejo.", "NO_ARRANCA", "El áncora bloquea el tren.", "Glucydur; espiral con curva Breguet")
tipo("volante_tornillos", "Volante con tornillos y puente", "regulacion", "Volante clásico con tornillos en su aro para equilibrarlo y ajustar su inercia.", "NO_ARRANCA", "El áncora bloquea el tren.", "Glucydur con tornillos de oro")
tipo("volante_jaula", "Volante con espiral (de la jaula)", "tourbillon", "Volante pequeño y liviano montado en el centro de la jaula del tourbillon.", "JAULA_QUIETA", "Sin volante la jaula queda bloqueada.", "Glucydur")
tipo("raqueta_micrometrica", "Raqueta micrométrica", "regulacion", "Regulador con tornillo y resorte que mueve la raqueta en pasos finísimos: una exigencia de los relojes ferroviarios.", "DESREGULADO", "No hay forma fina de regular la marcha.", "Acero")
tipo("regulador_tompion", "Regulador de disco", "regulacion", "Disco numerado que, al girarlo, acorta o alarga la parte activa del espiral para adelantar o atrasar.", "DESREGULADO", "No hay forma de regular la marcha.", "Plata y acero")
# Remontoir y puesta en hora
tipo("tija", "Tija (vástago de corona)", "remontoir", "Eje que une la corona con el mecanismo: según su posición, da cuerda o mueve las agujas.", "NO_DA_CUERDA", "La corona no llega al mecanismo.", "Acero")
tipo("tija_corona", "Tija con corona", "remontoir", "Vástago y corona que se reinstalan al encajar el movimiento en la caja.", "NO_DA_CUERDA", "No hay cómo dar cuerda ni ajustar la hora.", "Acero")
tipo("pinon_remontoir", "Piñón de remontoir", "remontoir", "Gira con la tija y transmite la cuerda hacia la rueda de corona.", "NO_DA_CUERDA", "La cuerda no avanza.", "Acero")
tipo("pinon_corredizo", "Piñón corredizo (embrague)", "remontoir", "Se desliza sobre la tija: hacia adentro engrana la cuerda; hacia afuera, la puesta en hora.", "NO_PONE_HORA", "No hay embrague entre cuerda y hora.", "Acero")
tipo("tirete", "Tirete", "remontoir", "Palanca que sigue a la tija cuando tiras la corona y fija sus posiciones.", "CORONA_SIN_POSICIONES", "La corona no queda en sus posiciones.", "Acero")
tipo("bascula", "Báscula", "remontoir", "Palanca guiada por el tirete que mueve el piñón corredizo entre cuerda y puesta en hora.", "NO_PONE_HORA", "El embrague no cambia de posición.", "Acero")
tipo("brida_tirete", "Brida del tirete (resorte de báscula)", "remontoir", "Placa elástica que mantiene tirete y báscula en su lugar y da los «clics» de cada posición.", "CORONA_SIN_POSICIONES", "Las palancas quedan sueltas.", "Acero templado")
tipo("resorte_tirete", "Resorte del tirete", "remontoir", "Lámina que fija las posiciones de la tija en movimientos de cuarzo.", "CORONA_SIN_POSICIONES", "La tija se sale o no tiene posiciones.", "Acero", pinzas=True)
tipo("rueda_puesta_hora", "Rueda de puesta en hora", "remontoir", "Lleva el giro de la corona hacia la rueda de minutos cuando ajustas la hora.", "NO_PONE_HORA", "La corona no mueve las agujas.", "Acero o latón")
tipo("palanca_lever_set", "Palanca de puesta en hora (lever set)", "remontoir", "En los relojes ferroviarios la hora solo se ajusta sacando esta palanca bajo el bisel: evita cambios accidentales.", "NO_PONE_HORA", "No hay forma de pasar a puesta en hora.", "Acero")
tipo("resorte_palanca_lever_set", "Resorte de la palanca", "remontoir", "Mantiene la palanca de puesta en hora en posición de cuerda o de ajuste. Está bajo tensión.", "NO_PONE_HORA", "La palanca no queda en posición.", "Acero templado", pinzas=True)
# Minutería
tipo("canon_minutos", "Cañón de minutos", "minuteria", "Tubo ajustado a fricción sobre el eje de la rueda de centro: lleva el minutero y permite moverlo al poner la hora.", "AGUJAS_QUIETAS", "El mecanismo late, pero las agujas no avanzan.", "Acero")
tipo("rueda_minutos", "Rueda de minutos", "minuteria", "Reduce 12 veces el giro del cañón para mover la rueda de horas.", "HORARIO_QUIETO", "El horario no avanza.", "Latón")
tipo("rueda_horas", "Rueda de horas", "minuteria", "Gira una vez cada 12 horas y lleva el horario.", "HORARIO_QUIETO", "El horario no avanza.", "Latón")
tipo("arandela_esfera", "Arandela de esfera", "minuteria", "Lámina curva que evita que la rueda de horas suba y roce la esfera.", "MARCHA_IRREGULAR", "El horario roza la esfera.", "Acero")
# Esfera y agujas
tipo("esfera", "Esfera", "esfera_agujas", "La cara del reloj: índices, números y ventanillas. Se coloca con las 12 arriba.", "INCOMPLETO", "Falta la esfera.", "Latón lacado")
tipo("esfera_esmalte", "Esfera de esmalte", "esfera_agujas", "Esmalte vítreo cocido sobre cobre: no se pule ni se moja, y una grieta fina («pelo») casi no tiene arreglo.", "INCOMPLETO", "Falta la esfera.", "Esmalte sobre cobre")
tipo("aguja_horas", "Aguja horaria", "esfera_agujas", "Se coloca primero, apuntando exactamente a las 12.", "INCOMPLETO", "Faltan agujas: el reloj no muestra la hora.", "Acero azulado o latón")
tipo("aguja_minutos", "Aguja minutera", "esfera_agujas", "Se coloca alineada con el horario a las 12.", "INCOMPLETO", "Faltan agujas.", "Acero azulado o latón")
tipo("segundero", "Segundero central", "esfera_agujas", "Aguja fina central; se coloca al final.", "INCOMPLETO", "Falta el segundero.", "Acero")
tipo("segundero_pequeno", "Segundero pequeño", "esfera_agujas", "Se monta sobre el eje de la cuarta rueda; su posición inicial da igual.", "INCOMPLETO", "Falta el segundero.", "Acero")
tipo("aguja_crono", "Segundero del cronógrafo", "esfera_agujas", "Aguja central del cronógrafo: debe quedar exactamente en cero.", "INCOMPLETO", "Falta la aguja del cronógrafo.", "Acero")
tipo("aguja_contador_minutos", "Aguja del contador de minutos", "esfera_agujas", "Marca los minutos cronometrados; se coloca en cero.", "INCOMPLETO", "Falta una aguja del contador.", "Acero")
tipo("aguja_contador_horas", "Aguja del contador de horas", "esfera_agujas", "Marca las horas cronometradas; se coloca en cero.", "INCOMPLETO", "Falta una aguja del contador.", "Acero")
tipo("aguja_tourbillon", "Indicador de segundos del tourbillon", "esfera_agujas", "Flecha sobre la jaula que, al dar una vuelta por minuto, marca los segundos.", "INCOMPLETO", "Falta el indicador.", "Acero azulado")
# Calendario
tipo("rueda_motriz_fecha", "Rueda motriz de la fecha", "calendario", "Gira una vez cada 24 h movida por la rueda de horas; su dedo empuja el disco de fechas un día.", "FECHA_NO_CAMBIA", "Nada empuja el disco de fechas.", "Latón")
tipo("rueda_salto_instantaneo", "Rueda de salto instantáneo", "calendario", "Acumula energía durante horas y la libera a medianoche: la fecha cambia de golpe.", "FECHA_NO_CAMBIA", "Nada empuja el disco de fechas.", "Latón")
tipo("resorte_salto_instantaneo", "Resorte de salto instantáneo", "calendario", "Se tensa poco a poco y dispara el cambio de fecha en un instante. Está bajo tensión.", "FECHA_NO_CAMBIA", "La fecha cambia lento o no cambia.", "Acero templado", pinzas=True)
tipo("disco_fecha", "Disco de fechas", "calendario", "Anillo con los números 1 a 31 que se asoma por la ventanilla.", "FECHA_NO_CAMBIA", "No hay indicación de fecha.", "Latón impreso")
tipo("salteador_fecha", "Salteador de fecha", "calendario", "Resorte con punta que deja cada número centrado en la ventanilla. Está bajo tensión.", "FECHA_DESALINEADA", "La fecha queda a medio camino.", "Acero templado", pinzas=True)
tipo("corrector_fecha", "Corrector rápido de fecha", "calendario", "Rueda que avanza la fecha desde la corona sin dar vueltas completas a las agujas.", "SIN_CORRECCION", "No se puede corregir la fecha desde la corona.", "Acero")
tipo("estrella_dias", "Estrella de los días", "calendario", "Rueda de siete puntas que hace avanzar el disco de días.", "DIA_NO_CAMBIA", "El día no avanza.", "Acero")
tipo("disco_dias", "Disco de días", "calendario", "Disco con los días de la semana.", "DIA_NO_CAMBIA", "No hay indicación del día.", "Latón impreso")
tipo("salteador_dias", "Salteador de días", "calendario", "Resorte que deja el día centrado en la ventanilla. Está bajo tensión.", "FECHA_DESALINEADA", "El día queda a medio camino.", "Acero templado", pinzas=True)
# Automático
tipo("rotor", "Rotor (masa oscilante)", "automatico", "Media luna pesada que gira con el movimiento de la muñeca y carga el muelle real.", "SIN_AUTOCUERDA", "No hay carga automática.", "Latón o tungsteno, a menudo grabado")
tipo("rueda_inversora", "Rueda inversora", "automatico", "Con trinquetes internos convierte el giro del rotor, en ambos sentidos, en un solo sentido de carga. Algunas casas las fabrican rojas.", "SIN_AUTOCUERDA", "El rotor gira sin cargar.", "Aleación liviana o acero")
tipo("rueda_reduccion", "Rueda de reducción del automático", "automatico", "Reduce la velocidad del rotor y entrega la fuerza al rochete.", "SIN_AUTOCUERDA", "El rotor gira sin cargar.", "Latón")
tipo("rueda_transmision", "Rueda de transmisión del automático", "automatico", "Rueda que recibe el movimiento del rotor y lo lleva hacia el rochete.", "SIN_AUTOCUERDA", "El rotor gira sin cargar.", "Latón")
tipo("palanca_magica", "Palanca mágica (Magic Lever)", "automatico", "Palanca de dos uñetas sobre un pasador excéntrico: empuja y tira de una rueda para cargar en ambos sentidos con muy pocas piezas.", "SIN_AUTOCUERDA", "El rotor gira sin cargar.", "Acero")
# Cronógrafo
tipo("rueda_pilares", "Rueda de pilares", "cronografo", "Castillo de columnas que ordena arranque, parada y vuelta a cero: cada pulsación la hace avanzar un diente.", "CRONO_NO_ARRANCA", "Nada coordina las palancas del cronógrafo.", "Acero pulido")
tipo("salteador_rueda_pilares", "Salteador de la rueda de pilares", "cronografo", "Resorte que mantiene la rueda de pilares quieta en cada posición. Está bajo tensión.", "CRONO_NO_SE_DETIENE", "La rueda de pilares no queda en posición.", "Acero templado", pinzas=True)
tipo("leva_conmutacion", "Leva de conmutación", "cronografo", "Leva oscilante que reemplaza a la rueda de pilares: más simple de fabricar, con un pulsador algo más firme.", "CRONO_NO_ARRANCA", "Nada coordina las palancas del cronógrafo.", "Acero")
tipo("pinon_oscilante", "Piñón oscilante", "cronografo", "Piñón que se inclina para engranar con la rueda de cronógrafo al arrancar.", "CRONO_NO_ARRANCA", "El cronógrafo no recibe movimiento.", "Acero")
tipo("palanca_embrague", "Palanca de embrague con rueda de acoplamiento", "cronografo", "Acerca o aleja una rueda que conecta el movimiento con la rueda de cronógrafo (embrague horizontal).", "CRONO_NO_ARRANCA", "El cronógrafo no recibe movimiento.", "Acero y latón")
tipo("resorte_embrague", "Resorte de embrague", "cronografo", "Empuja la palanca de embrague hacia la rueda de cronógrafo. Está bajo tensión.", "CRONO_NO_ARRANCA", "El embrague no engrana.", "Acero templado", pinzas=True)
tipo("rueda_cronografo", "Rueda de cronógrafo", "cronografo", "Rueda central de dientes finísimos: lleva el segundero del cronógrafo y un corazón para volver a cero.", "CRONO_NO_ARRANCA", "No hay segundero de cronógrafo que mover.", "Latón dorado")
tipo("rueda_intermedia_contador", "Rueda intermedia del contador", "cronografo", "Recibe el toque del dedo de la rueda de cronógrafo una vez por minuto y avanza el contador.", "CONTADOR_QUIETO", "El contador de minutos no avanza.", "Acero")
tipo("rueda_contador_minutos", "Rueda contadora de minutos", "cronografo", "Lleva la aguja del contador de minutos y su propio corazón de puesta a cero.", "CONTADOR_QUIETO", "No hay contador de minutos.", "Latón")
tipo("rueda_contador_horas", "Rueda contadora de horas", "cronografo", "Lleva la aguja del contador de horas y su corazón de puesta a cero.", "CONTADOR_QUIETO", "No hay contador de horas.", "Latón")
tipo("palanca_mando", "Palanca de mando", "cronografo", "Transmite la pulsación del botón a la rueda de pilares o a la leva.", "CRONO_NO_ARRANCA", "Los pulsadores no actúan.", "Acero")
tipo("resorte_palanca_mando", "Resorte de la palanca de mando", "cronografo", "Devuelve la palanca de mando a su lugar después de cada pulsación. Está bajo tensión.", "CRONO_NO_ARRANCA", "El pulsador queda hundido.", "Acero templado", pinzas=True)
tipo("freno_cronografo", "Freno del cronógrafo", "cronografo", "Detiene la rueda de cronógrafo al pulsar parada.", "CRONO_NO_SE_DETIENE", "La aguja sigue girando por inercia.", "Acero")
tipo("martillo", "Martillo de puesta a cero", "cronografo", "Golpea los corazones de las ruedas para que las agujas vuelvan a cero.", "CRONO_NO_VUELVE_A_CERO", "Las agujas no vuelven a cero.", "Acero")
tipo("resorte_martillos", "Resorte de los martillos", "cronografo", "Da la fuerza del golpe de puesta a cero. Está bajo tensión.", "CRONO_NO_VUELVE_A_CERO", "Los martillos no golpean.", "Acero templado", pinzas=True)
# Tourbillon
tipo("jaula_inferior", "Base de la jaula", "tourbillon", "Estructura inferior de la jaula giratoria; su piñón engrana con la tercera rueda.", "JAULA_QUIETA", "No hay jaula.", "Titanio o acero")
tipo("columna_jaula", "Columna de la jaula", "tourbillon", "Pilar que separa la base y la parte superior de la jaula.", "JAULA_QUIETA", "La jaula se deforma y traba.", "Acero")
tipo("jaula_superior", "Puente superior de la jaula", "tourbillon", "Cierra la jaula y sostiene el pivote del volante.", "JAULA_QUIETA", "El volante no tiene apoyo.", "Acero pulido")
tipo("puente_ancora_jaula", "Puente del áncora de la jaula", "tourbillon", "Diminuto puente que sostiene el áncora dentro de la jaula.", "JAULA_QUIETA", "El áncora se suelta dentro de la jaula.", "Acero")
tipo("chaton_tourbillon", "Chatón del puente del tourbillon", "tourbillon", "Anillo con rubí atornillado al puente: alojamiento superior del eje de la jaula.", "JAULA_QUIETA", "El eje de la jaula no tiene apoyo.", "Oro con rubí")
# Cuarzo
tipo("rotor_motor", "Rotor del motor paso a paso", "cuarzo", "Pequeño imán que avanza medio giro con cada pulso eléctrico, una vez por segundo.", "MOTOR_NO_GIRA", "No hay motor.", "Imán de samario-cobalto")
tipo("estator", "Estator", "cuarzo", "Pieza de hierro dulce que concentra el campo magnético de la bobina sobre el rotor.", "MOTOR_NO_GIRA", "El campo no llega al rotor.", "Hierro dulce")
tipo("bobina", "Bobina", "cuarzo", "Miles de vueltas de alambre finísimo: convierte el pulso eléctrico en magnetismo.", "MOTOR_NO_GIRA", "No hay campo magnético.", "Cobre esmaltado")
tipo("circuito", "Módulo electrónico con cristal de cuarzo", "cuarzo", "El cuarzo vibra 32.768 veces por segundo; el circuito divide esa señal hasta un pulso por segundo.", "SIN_ENERGIA", "No hay señal para el motor.", "Placa de circuito y cristal de cuarzo")
tipo("aislante", "Aislante del circuito", "cuarzo", "Lámina plástica que evita cortocircuitos entre la pila y el movimiento.", "SIN_ENERGIA", "Cortocircuito: la pila se descarga.", "Polímero")
# Encajado
tipo("anillo_encajado", "Anillo de encajado", "encajado", "Aro que ajusta el movimiento al diámetro interior de la caja.", "MOVIMIENTO_SUELTO", "El movimiento baila en la caja.", "Polímero o latón")
tipo("brida_encajado", "Brida de encajado", "encajado", "Pequeña garra atornillada que aprieta el movimiento contra la caja.", "MOVIMIENTO_SUELTO", "El movimiento baila en la caja.", "Acero")
tipo("caja", "Caja", "encajado", "Protege el movimiento; lleva el cristal y el tubo de la corona.", "SIN_PROTECCION", "El movimiento queda expuesto.", "Acero inoxidable")
tipo("caja_bolsillo", "Caja de bolsillo", "encajado", "Caja con colgante y argolla para la leontina.", "SIN_PROTECCION", "El movimiento queda expuesto.", "Chapado en oro")
tipo("caja_interior", "Caja interior", "encajado", "En los relojes de doble caja del siglo XVIII, la caja interior contiene el movimiento y el cristal.", "SIN_PROTECCION", "El movimiento queda expuesto.", "Plata")
tipo("caja_exterior", "Caja exterior", "encajado", "Segunda caja que envuelve y protege a la interior.", "SIN_PROTECCION", "La caja interior queda expuesta.", "Plata repujada")
tipo("caja_pulsadores", "Caja de cronógrafo con pulsadores", "encajado", "Caja con los botones de arranque/parada y de puesta a cero.", "SIN_PROTECCION", "El movimiento queda expuesto.", "Acero inoxidable")
tipo("cristal", "Cristal", "encajado", "Acrílico, mineral, zafiro o vidrio: protege la esfera. El acrílico se pule; el zafiro casi no se raya pero puede astillarse.", "SIN_PROTECCION", "La esfera queda expuesta.", "Según el reloj")
tipo("bisel", "Bisel", "encajado", "Aro que sujeta el cristal sobre la caja.", "SIN_PROTECCION", "El cristal no queda sujeto.", "Acero o metal precioso")
tipo("corona", "Corona", "encajado", "Botón para dar cuerda y ajustar la hora; en relojes de buceo se enrosca para sellar.", "NO_DA_CUERDA", "No hay cómo dar cuerda.", "Acero")
tipo("junta", "Junta del fondo", "encajado", "Anillo de goma que sella la caja contra agua y polvo.", "NO_HERMETICO", "La caja no sella.", "Caucho nitrilo")
tipo("fondo", "Fondo", "encajado", "Tapa trasera: a presión, enroscada o de exhibición con cristal.", "NO_HERMETICO", "La caja queda abierta.", "Acero")

# ------------------------------------------------------------------ constructores de piezas
def base(id, tp, lado, xy, forma, rot=0.0, rotI=True, espI=True, capa=1, **kw):
    assert tp in T, tp
    d = {"id": id, "tipo": tp, "lado": lado, "x": r1(xy[0]), "y": r1(xy[1]), "rot": r1(rot),
         "rotImporta": rotI, "espejoImporta": espI, "capa": capa, "forma": forma}
    for k, v in kw.items():
        if v is not None:
            d[k] = v
    if T[tp].get("requierePinzas"):
        d["pinzas"] = True
    return d

def rueda(id, tp, lado, xy, r, z, pinon=None, brazos=5, mat="laton", capa=2, estilo=None, **kw):
    f = {"t": "rueda", "r": r1(r), "dientes": z, "brazos": brazos, "mat": mat}
    if pinon: f["pinon"] = pinon
    if estilo: f["estilo"] = estilo
    return base(id, tp, lado, xy, f, rotI=False, espI=True, capa=capa, **kw)

def tornillo(id, sobre, lado, xy, cab=1.0, giros=2.0, rosca="derecha", capa=6, nombre=None, tp="tornillo", **kw):
    f = {"t": "tornillo", "r": r1(2.4 + cab * 2.2), "acabado": "azulado" if cab <= 1.4 else "pulido"}
    d = base(id, tp, lado, xy, f, rotI=False, espI=False, capa=capa, variante="tornillo_" + sobre, sobre=sobre,
             tornillo={"cabeza_mm": cab, "giros": giros, "rosca": rosca}, **kw)
    if nombre: d["nombre"] = nombre
    return d

def palanca(id, tp, lado, xy, pts, w=5, capa=3, mat="acero", curva=False, **kw):
    f = {"t": "palanca", "pts": pts, "w": w, "mat": mat}
    if curva: f["curva"] = True
    return base(id, tp, lado, xy, f, rot=0, rotI=True, espI=True, capa=capa, **kw)

def aguja(id, tp, lado, xy, estilo, largo, rotI=True, capa=8, **kw):
    return base(id, tp, lado, xy, {"t": "aguja", "estilo": estilo, "largo": largo}, rot=0, rotI=rotI, espI=True, capa=capa, **kw)

class Nivel:
    def __init__(self, meta):
        self.meta = meta; self.items = []; self.n = 0; self.pos = {}
    def add(self, *ps):
        self.n += 1
        for p in ps:
            p["paso"] = self.n
            self.items.append(p)
            self.pos[p["id"]] = (p["x"], p["y"])
        return ps
    def xy(self, id):
        return self.pos[id]

def puente(L, id, tp, lado, cubre, nt, margen=12, extra=(), extra_r=9, mat="rodio", deco="cotes", capa=4, cab=1.2, giros=2.5, nombre=None, evitar_extra=True, pies=(), **kw):
    centers = [L.xy(c) for c in cubre]
    pts = []
    for c in centers: pts += circle_pts(c, margen)
    for e in list(extra) + list(pies): pts += circle_pts(e, extra_r)
    poly = decimate(hull(pts), 16)
    c = centroid(poly)
    prev = [(q["x"], q["y"]) for q in L.items if q["lado"] == lado and q["forma"]["t"] in ("tornillo", "rueda")] + RESERVADOS.get(lado, [])
    sc = choose_screws(poly, centers + (list(extra) if evitar_extra else []) + prev, nt) if nt else []
    f = {"t": "puente", "poly": loc(poly, c), "mat": mat, "deco": deco,
         "rubies": loc(centers, c), "agujeros": loc(sc, c)}
    p = base(id, tp, lado, c, f, rot=0, capa=capa, cubre=list(cubre), nombre=nombre, **kw)
    ts = [tornillo(f"{id}_t{i+1}", id, lado, s, cab=cab, giros=giros, capa=capa + 1,
                   nombre=f"Tornillo del {(nombre or T[tp]['nombre']).lower()}") for i, s in enumerate(sc)]
    return p, ts

def placa(id, tp, lado, ancla, poly_world, tornillos_world, cab=1.0, giros=2.0, capa=4, mat="acero", deco="perlage", nombre=None, **kw):
    f = {"t": "placa", "poly": loc(poly_world, ancla), "mat": mat, "deco": deco, "agujeros": loc(tornillos_world, ancla)}
    p = base(id, tp, lado, ancla, f, rot=0, capa=capa, nombre=nombre, **kw)
    ts = [tornillo(f"{id}_t{i+1}", id, lado, s, cab=cab, giros=giros, capa=capa + 1,
                   nombre=f"Tornillo de la {(nombre or T[tp]['nombre']).lower()}") for i, s in enumerate(tornillos_world)]
    return p, ts

def volante_con_puente(id, tp, lado, centro, r, pies, brazos=3, espiral="plana", capa=6, extra=None, mat="glucydur"):
    pts = circle_pts(centro, 11)
    for p in pies: pts += circle_pts(p, 9)
    poly = decimate(hull(pts))
    f = {"t": "volante", "r": r, "brazos": brazos, "espiral": espiral, "mat": mat,
         "puente": loc(poly, centro), "agujeros": loc(pies, centro)}
    if extra: f.update(extra)
    v = base(id, tp, lado, centro, f, rot=0, rotI=True, espI=True, capa=capa)
    ts = [tornillo(f"{id}_t{i+1}", id, lado, p, cab=1.2, giros=2.5, capa=capa + 1, nombre="Tornillo del puente de volante") for i, p in enumerate(pies)]
    return v, ts

def ancora(id, lado, piv, hacia, capa=4, tp="ancora", **kw):
    f = {"t": "ancora", "largo": r1(dist(piv, hacia)), "ancho": 16}
    return base(id, tp, lado, piv, f, rot=ang(piv, hacia), rotI=True, espI=True, capa=capa, **kw)

def foot(centro, delta, d=86):
    return pol(d, ang((0, 0), centro) + delta)

# Encajado común ---------------------------------------------------------------
def caja_pulsera(L, corona_xy=(122, 0), estilo="pulsera", fondo="presion", con_anillo=True, bridas=False, tija=True, rotor=None, pulsadores=False, cristal_aparte=None, bisel=False):
    seq = []
    if con_anillo:
        L.add(base("anillo_encajado", "anillo_encajado", "reverso", (0, 0), {"t": "anillo", "r_in": 100, "r_out": 108}, rotI=False, espI=False, capa=9))
    tp = "caja_pulsadores" if pulsadores else "caja"
    fc = {"t": "caja", "r": 116, "estilo": estilo, "asas": True}
    if pulsadores: fc["pulsadores"] = [[r1(x) for x in pol(118, 60)], [r1(x) for x in pol(118, 120)]]
    L.add(base("caja", tp, "frente", (0, 0), fc, rot=0, rotI=True, espI=True, capa=10))
    if cristal_aparte:
        L.add(base("cristal", "cristal", "frente", (0, 0), {"t": "cristal", "r": 104, "material": cristal_aparte}, rotI=False, espI=False, capa=11))
    if bisel:
        L.add(base("bisel", "bisel", "frente", (0, 0), {"t": "bisel", "r": 116}, rotI=False, espI=False, capa=12))
    if tija:
        L.add(base("tija_corona", "tija_corona", "frente", (corona_xy[0] - 22, corona_xy[1]), {"t": "tija", "largo": 50, "corona": True}, rot=90, capa=10))
    if bridas:
        b1, b2 = pol(103, 135), pol(103, 315)
        L.add(base("brida_encajado_1", "brida_encajado", "reverso", b1, {"t": "garra", "largo": 14}, rot=r1(ang((0, 0), b1)), capa=10),
              base("brida_encajado_2", "brida_encajado", "reverso", b2, {"t": "garra", "largo": 14}, rot=r1(ang((0, 0), b2)), capa=10))
        L.add(tornillo("brida_encajado_1_t", "brida_encajado_1", "reverso", pol(97, 135), cab=1.0, capa=11, nombre="Tornillo de brida de encajado"),
              tornillo("brida_encajado_2_t", "brida_encajado_2", "reverso", pol(97, 315), cab=1.0, capa=11, nombre="Tornillo de brida de encajado"))
    if rotor:
        L.add(base("rotor", "rotor", "reverso", (0, 0), {"t": "rotor", "r": 92, "arco": 180, "deco": rotor}, rotI=False, espI=True, capa=12))
        L.add(tornillo("rotor_t", "rotor", "reverso", (0, 0), cab=1.6, giros=2.0, capa=13, nombre="Tornillo del rotor"))
    L.add(base("junta", "junta", "reverso", (0, 0), {"t": "junta", "r": 106}, rotI=False, espI=False, capa=13))
    L.add(base("fondo", "fondo", "reverso", (0, 0), {"t": "fondo", "r": 112, "cierre": fondo}, rotI=True if fondo != "presion" else False, espI=True, capa=14))

# ------------------------------------------------------------------ NIVELES
NIVELES = []
RESERVADOS = {}  # ejes de ruedas del nivel (se llenan en una primera pasada) para que los tornillos no caigan sobre ellos

def meta(**kw):
    kw.setdefault("prob_espejo", 0.25)
    return kw

# ---------------------------------------------------------------- N01 Unitas 6497
def n01():
    L = Nivel(meta(
        id="n01_unitas_6497", orden=1, dificultad=1,
        titulo="El reloj de la escuela",
        reloj={"nombre": "Reloj de bolsillo de taller-escuela", "tipo": "Bolsillo, apertura Lépine (corona a las 12)", "ilustracion": "Movimiento esquemático propio, sin marcas ni logotipos"},
        casa="Unitas (Suiza); hoy en la familia ETA", calibre="Unitas 6497", anio=1950, epoca="Mediados del siglo XX",
        specs={"diametro_mm": 36.6, "lineas": "16½'''", "alto_mm": 4.5, "rubies": 17, "frecuencia_ah": 18000, "reserva_h": 46, "cuerda": "Manual", "funciones": ["Horas", "Minutos", "Segundero pequeño"]},
        historia="Calibre grande y robusto de los años 50, pensado para relojes de bolsillo. Por su tamaño y su lógica clara se usa para aprender en escuelas de relojería.",
        sabias_que=["En los años 90 estos movimientos de bolsillo se pusieron de moda dentro de relojes de pulsera de gran tamaño.",
                     "El tornillo de la rueda de corona tiene rosca izquierda: se aprieta girando en sentido antihorario."],
        cliente={"nombre": "Profesora Marta Sepúlveda", "perfil": "Docente de un taller-escuela de relojería en Santiago", "pedido": "Desarmé este movimiento frente a mis alumnos. ¿Puede dejarlo andando para la clase del lunes?", "plazo_dias": 3},
        pago_base=30000, reputacion=5, memorice_s=10, prob_espejo=0.0, rot_spawn_max=45,
        orientacion={"corona": 12, "segundero_pequeno": 6},
        preensamblado=["Platina con rubíes", "Mecanismo de remontoir y puesta en hora"],
        mecanicas_nuevas=["mover", "rotar", "voltear", "atornillar", "rosca_izquierda", "lista", "info", "memorice", "pistas", "probar_marcha"],
        herramientas_requeridas=["destornilladores_basicos", "pinzas_laton", "lupa_x3", "portamovimientos"],
        defectos=["suciedad_general"],
        fuentes=["https://ranfft.org/caliber/10348-Unitas-6497", "https://monochrome-watches.com/history-eta-unitas-6497-and-6498-hand-wound-lepine-savonette-movements-technical-guide", "https://archive.horlogerie-suisse.com/Theoriehorlogerie/disassembling-mechanical-watch.html"]))
    C, B, Tt, F, E, P, BAL, CW = (0, 0), (-22, -40), (24, 28), (0, 52), (-26, 62), (-42, 50), (-58, 34), (6, -66)
    rR = 24
    L.add(rueda("barrilete", "barrilete", "reverso", B, dist(B, C) - 6, 96, brazos=0, capa=1, estilo="barrilete"))
    L.add(rueda("rueda_centro", "rueda_centro", "reverso", C, dist(C, Tt) - 5, 80, pinon=6))
    p, ts = puente(L, "puente_barrilete", "puente_barrilete", "reverso", ["barrilete", "rueda_centro"], 3, margen=14, extra=[CW], extra_r=11)
    L.add(p); L.add(*ts)
    L.add(rueda("rochete", "rochete", "reverso", B, rR, 60, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rochete_t", "rochete", "reverso", B, cab=1.6, giros=2.0, capa=7, nombre="Tornillo del rochete"))
    L.add(rueda("rueda_corona", "rueda_corona", "reverso", CW, dist(B, CW) - rR, 36, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rueda_corona_t", "rueda_corona", "reverso", CW, cab=1.2, giros=2.0, rosca="izquierda", capa=7, nombre="Tornillo de la rueda de corona (rosca izquierda)"))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, dist(Tt, F) - 5, 75, pinon=5))
    L.add(rueda("cuarta_rueda", "cuarta_rueda", "reverso", F, dist(F, E) - 4, 80, pinon=5))
    L.add(rueda("rueda_escape", "rueda_escape", "reverso", E, 13, 15, pinon=4, mat="acero", estilo="escape"))
    p, ts = puente(L, "puente_rodaje", "puente_rodaje", "reverso", ["tercera_rueda", "cuarta_rueda", "rueda_escape"], 2, margen=12)
    L.add(p); L.add(*ts)
    L.add(ancora("ancora", "reverso", P, BAL))
    p, ts = puente(L, "puente_ancora", "puente_ancora", "reverso", ["ancora"], 2, margen=8, extra=[(-58, 64)], extra_r=8, evitar_extra=False)
    L.add(p); L.add(*ts)
    v, ts = volante_con_puente("volante", "volante", "reverso", BAL, 26, [foot(BAL, -26)], extra={"raqueta": True})
    L.add(v); L.add(*ts)
    L.add(rueda("canon_minutos", "canon_minutos", "frente", (0, 0), 7, 12, brazos=0, mat="acero", capa=1, estilo="pinon"))
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (24, -10), 17, 40, pinon=8, capa=2))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 16, 32, brazos=0, capa=3))
    L.add(base("esfera", "esfera", "frente", (0, 0), {"t": "esfera", "r": 98, "estilo": "bolsillo_arabigo", "subseg": [0, 52]}, capa=5))
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "pera", 50, capa=6))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "pera", 76, capa=7))
    L.add(aguja("segundero_pequeno", "segundero_pequeno", "frente", (0, 52), "baston", 16, rotI=False, capa=7))
    return L

# ---------------------------------------------------------------- N02 Miyota 2035
def n02():
    L = Nivel(meta(
        id="n02_miyota_2035", orden=2, dificultad=2, titulo="El cuarzo del cajón",
        reloj={"nombre": "Reloj de cuarzo de tres agujas", "tipo": "Pulsera, caja de acero con fondo a presión", "ilustracion": "Esquemática propia"},
        casa="Miyota (grupo Citizen, Japón)", calibre="Miyota 2035", anio=None, epoca="Cuarzo contemporáneo",
        specs={"medidas_mm": "15,3 × 18,5", "lineas": "6¾ × 8'''", "alto_mm": 3.15, "rubies": 0, "frecuencia_cuarzo_hz": 32768, "pila": "SR626SW (377)", "autonomia_pila": "≈ 3 años", "precision": "±20 s/mes", "funciones": ["Horas", "Minutos", "Segundero central"]},
        historia="Uno de los movimientos más fabricados del mundo: su fabricante informa miles de millones de unidades. Simple, económico y fácil de reemplazar.",
        sabias_que=["El cristal de cuarzo vibra 32.768 veces por segundo: es 2 elevado a 15, fácil de dividir hasta un pulso por segundo.",
                    "El primer reloj de pulsera de cuarzo a la venta se presentó en Japón en diciembre de 1969."],
        cliente={"nombre": "Tomás Ibarra", "perfil": "Estudiante universitario en Valparaíso", "pedido": "Era de mi abuelo y quedó años en un cajón. No anda y el cristal está trizado.", "plazo_dias": 2},
        pago_base=40000, reputacion=6, memorice_s=9, prob_espejo=0.1, rot_spawn_max=90,
        orientacion={"corona": 3},
        preensamblado=["Platina"],
        mecanicas_nuevas=["espejo", "polaridad_pila", "encajado", "fondo_presion"],
        herramientas_requeridas=["cuchilla_fondo"],
        defectos=["pila_agotada", "contactos_sulfatados", "cristal_mineral_trizado"],
        fuentes=["https://calibercorner.com/miyota-caliber-2035", "https://miyotamovement.com/jp/uploads/product/product_rHCdc0I4w7iV1e3lyX.pdf"]))
    # frente: remontoir (corona a las 3 => +x)
    L.add(base("tija", "tija", "frente", (72, 0), {"t": "tija", "largo": 54}, rot=90, capa=2))
    L.add(palanca("tirete", "tirete", "frente", (40, -18), [[0, 0], [0, -10], [8, -18], [18, -18]]))
    L.add(palanca("resorte_tirete", "resorte_tirete", "frente", (24, -40), [[-10, 6], [0, 0], [14, -4], [26, 2]], w=2.5, curva=True, capa=4))
    L.add(tornillo("resorte_tirete_t", "resorte_tirete", "frente", (24, -40), cab=1.0, capa=5, nombre="Tornillo del resorte del tirete"))
    L.add(rueda("rueda_puesta_hora", "rueda_puesta_hora", "frente", (46, 18), 9, 20, brazos=0, mat="acero"))
    # reverso: tren, motor, circuito, pila (corona a las 9 => -x)
    C, Tt, Q, RM = (0, 0), (30, -18), (-24, 22), (-34, 44)
    L.add(rueda("rueda_central", "rueda_central_cuarzo", "reverso", C, 30, 60, pinon=5, capa=1))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, 16, 40, pinon=4))
    L.add(rueda("rueda_segundos", "rueda_segundos_central", "reverso", C, 17, 54, pinon=4, capa=3))
    L.add(rueda("quinta_rueda", "quinta_rueda", "reverso", Q, 12, 36, pinon=3))
    L.add(base("rotor_motor", "rotor_motor", "reverso", RM, {"t": "rotor_motor", "r": 6}, rotI=False, espI=False, capa=2))
    p, ts = puente(L, "puente_rodaje", "puente_rodaje", "reverso", ["rueda_central", "tercera_rueda", "quinta_rueda", "rotor_motor"], 2, margen=10, mat="plastico", deco="liso", nombre="Puente de rodaje (plástico)")
    L.add(p); L.add(*ts)
    est = [(-46, 40), (-22, 36), (-20, 52), (-34, 60), (-50, 54), (-64, 26), (-66, -26), (-56, -30), (-54, 22)]
    L.add(base("estator", "estator", "reverso", RM, {"t": "placa", "poly": loc(est, RM), "mat": "hierro", "deco": "liso", "agujeros": []}, capa=5))
    L.add(base("bobina", "bobina", "reverso", (-62, -2), {"t": "bobina", "largo": 50, "ancho": 14}, rot=0, capa=6))
    L.add(tornillo("bobina_t", "bobina", "reverso", (-62, -34), cab=1.0, capa=7, nombre="Tornillo de la bobina"))
    circ = [(-8, 46), (24, 26), (56, 10), (72, 32), (60, 62), (30, 80), (0, 76), (-12, 64)]
    p, ts = placa("circuito", "circuito", "reverso", (30, 50), circ, [(52, 22)], mat="circuito", deco="pistas", capa=6)
    p["forma"]["cuarzo"] = [-30, 16]
    L.add(p); L.add(*ts)
    ais = [(4, 50), (28, 34), (56, 22), (64, 36), (54, 58), (28, 72), (6, 66)]
    L.add(base("aislante", "aislante", "reverso", (32, 50), {"t": "placa", "poly": loc(ais, (32, 50)), "mat": "aislante", "deco": "liso", "agujeros": []}, capa=8))
    Bt = (34, 46)
    L.add(palanca("brida_pila", "brida_pila", "reverso", Bt, [[-30, -18], [0, -32], [30, -18]], w=4, capa=10))
    L.add(tornillo("brida_pila_t", "brida_pila", "reverso", (64, 28), cab=1.0, capa=11, nombre="Tornillo de la brida de la pila"))
    L.add(base("pila", "pila", "reverso", Bt, {"t": "pila", "r": 32, "codigo": "SR626SW"}, rotI=False, espI=True, capa=9))
    # frente: minutería, esfera y agujas
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (22, 14), 13, 30, pinon=6))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 15, 36, brazos=0, capa=3))
    L.add(base("arandela_esfera", "arandela_esfera", "frente", (0, 0), {"t": "arandela", "r": 17}, rotI=False, espI=True, capa=4))
    L.add(base("esfera", "esfera", "frente", (0, 0), {"t": "esfera", "r": 98, "estilo": "baston_moderno"}, capa=5))
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "baston", 48, capa=6))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "baston", 74, capa=7))
    L.add(aguja("segundero", "segundero", "frente", (0, 0), "fina", 84, rotI=False, capa=8))
    # encajado (la tija ya está puesta: se agrega solo la corona)
    L.add(base("anillo_encajado", "anillo_encajado", "reverso", (0, 0), {"t": "anillo", "r_in": 100, "r_out": 108}, rotI=False, espI=False, capa=9))
    L.add(base("caja", "caja", "frente", (0, 0), {"t": "caja", "r": 116, "estilo": "pulsera", "asas": True}, capa=10))
    L.add(base("corona", "corona", "frente", (124, 0), {"t": "corona", "r": 9}, rot=90, rotI=True, espI=False, capa=11))
    L.add(base("junta", "junta", "reverso", (0, 0), {"t": "junta", "r": 106}, rotI=False, espI=False, capa=12))
    L.add(base("fondo", "fondo", "reverso", (0, 0), {"t": "fondo", "r": 112, "cierre": "presion"}, rotI=False, espI=True, capa=13))
    return L

# ---------------------------------------------------------------- N03 Catalina y caracol
def n03():
    L = Nivel(meta(
        id="n03_catalina_caracol", orden=3, dificultad=3, titulo="El inglés del remate",
        reloj={"nombre": "Reloj de bolsillo de doble caja con escape de catalina y caracol", "tipo": "Bolsillo de llave, doble caja de plata", "ilustracion": "Esquemática propia, inspirada en el tipo histórico"},
        casa="Taller londinense (tipo histórico, sin firma específica)", calibre="Escape de catalina (verge) con caracol (fusee)", anio=1780, epoca="Siglo XVIII",
        specs={"diametro_mm_aprox": 38, "frecuencia_ah": 17280, "reserva_h": 30, "cuerda": "Con llave, a través de la esfera", "funciones": ["Horas", "Minutos"], "nota": "Valores típicos aproximados para la simulación: cada reloj de la época variaba según su tren."},
        historia="Antes del áncora suiza, los relojes de bolsillo usaban el escape de catalina y un caracol con cadena para igualar la fuerza del muelle. Las platinas se unían con pasadores, no con tornillos.",
        sabias_que=["El escape de catalina nació en los relojes de torre medievales y se usó en bolsillo durante siglos.",
                    "La cadena del caracol tiene cientos de eslabones remachados a mano: cortarla era un desastre."],
        cliente={"nombre": "Don Aurelio Contreras", "perfil": "Anticuario del Persa Biobío, Santiago", "pedido": "Lo compré en un remate. Dicen que es inglés del 1700. ¿Se puede hacer andar sin dañarlo?", "plazo_dias": 6},
        pago_base=70000, reputacion=8, memorice_s=9, prob_espejo=0.15, rot_spawn_max=180,
        orientacion={"colgante": 12, "agujero_cuerda": "esfera"},
        preensamblado=["Platina de pilares (con sus cuatro pilares)"],
        mecanicas_nuevas=["pasadores", "cadena_caracol", "llave_cuerda", "esfera_esmalte"],
        herramientas_requeridas=["llave_cuerda"],
        defectos=["cadena_oxidada", "esmalte_pelo", "cristal_vidrio_roto"],
        fuentes=[]))
    C, B, FU, Tt, K, CAT, BAL = (0, 0), (-40, 22), (30, 32), (-24, -22), (-2, -46), (30, -50), (30, -52)
    L.add(rueda("barrilete", "barrilete_caracol", "reverso", B, 28, 0, brazos=0, capa=1, estilo="tambor"))
    L.add(base("caracol", "caracol", "reverso", FU, {"t": "caracol", "r_cono": 22, "r_rueda": r1(dist(FU, C) - 6), "dientes": 72}, rotI=False, espI=True, capa=1))
    L.add(rueda("rueda_centro", "rueda_centro", "reverso", C, dist(C, Tt) - 6, 72, pinon=6))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, dist(Tt, K) - 5, 60, pinon=6))
    L.add(rueda("rueda_contrapunto", "rueda_contrapunto", "reverso", K, 18, 48, pinon=5, estilo="contrapunto"))
    L.add(base("rueda_catalina", "rueda_catalina", "reverso", (CAT[0], CAT[1] + 10), {"t": "catalina", "largo": 34, "alto": 8, "dientes": 15}, rot=90, capa=3))
    L.add(base("contrapotenza", "contrapotenza", "reverso", (52, -40), {"t": "bloque", "w": 10, "h": 14}, rot=0, capa=3))
    L.add(tornillo("contrapotenza_t", "contrapotenza", "reverso", (52, -46), cab=1.0, capa=4, nombre="Tornillo de la contrapotenza"))
    L.add(palanca("tope_caracol", "tope_caracol", "reverso", (54, 18), [[0, 0], [-10, 4], [-16, 10]], w=4, capa=3))
    pil = [pol(86, a) for a in (40, 140, 220, 320)]
    L.add(base("platina_superior", "platina_superior", "reverso", (0, 0), {"t": "platina_superior", "r": 92, "pilares": loc(pil, (0, 0)), "calados": True}, rot=0, capa=5))
    L.add(*[base(f"pasador_pilar_{i+1}", "pasador", "reverso", p, {"t": "pasador", "r": 2.6}, rotI=False, espI=False, capa=6, variante="pasador_pilar", nombre="Pasador de pilar") for i, p in enumerate(pil)])
    mid = ((B[0] + FU[0]) / 2, (B[1] + FU[1]) / 2 + 14)
    L.add(base("cadena_caracol", "cadena_caracol", "reverso", mid, {"t": "cadena", "desde": loc([B], mid)[0], "hasta": loc([FU], mid)[0], "r_desde": 28, "r_hasta": 20}, rotI=False, espI=True, capa=6))
    L.add(rueda("rochete_armado", "rochete_armado", "reverso", B, 12, 30, brazos=0, mat="acero", capa=7))
    L.add(palanca("trinquete_armado", "trinquete_armado", "reverso", (-26, 10), [[0, 0], [-6, -6], [-10, -4]], w=3, capa=7))
    L.add(palanca("resorte_trinquete_armado", "resorte_trinquete_armado", "reverso", (-20, 2), [[0, 0], [6, -4], [12, 0]], w=2, curva=True, capa=8))
    L.add(tornillo("trinquete_armado_t", "trinquete_armado", "reverso", (-26, 10), cab=1.0, capa=9, nombre="Tornillo del trinquete de armado"))
    L.add(base("volante_vara", "volante_vara", "reverso", BAL, {"t": "volante", "r": 32, "brazos": 3, "espiral": "plana", "mat": "acero"}, rotI=False, espI=True, capa=8))
    pc = hull(circle_pts(BAL, 18) + circle_pts((0, -84), 10))
    cc = centroid(pc)
    L.add(base("puente_volante_calado", "puente_volante_calado", "reverso", cc, {"t": "puente", "poly": loc(decimate(pc), cc), "mat": "oro", "deco": "calado", "rubies": loc([BAL], cc), "agujeros": loc([(0, -84)], cc)}, capa=9))
    L.add(tornillo("puente_volante_calado_t", "puente_volante_calado", "reverso", (0, -84), cab=1.4, capa=10, nombre="Tornillo del puente de volante"))
    L.add(base("regulador_tompion", "regulador_tompion", "reverso", (-44, -40), {"t": "disco_reglaje", "r": 14}, rot=0, capa=9))
    L.add(tornillo("regulador_tompion_t", "regulador_tompion", "reverso", (-44, -40), cab=1.0, capa=10, nombre="Tornillo del regulador"))
    # frente
    L.add(rueda("canon_minutos", "canon_minutos", "frente", (0, 0), 7, 12, brazos=0, mat="acero", capa=1, estilo="pinon"))
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (-24, 14), 16, 36, pinon=7))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 15, 36, brazos=0, capa=3))
    L.add(base("esfera", "esfera_esmalte", "frente", (0, 0), {"t": "esfera", "r": 96, "estilo": "esmalte_romano", "agujero_cuerda": [r1(-FU[0]), r1(FU[1])]}, capa=5))
    L.add(*[base(f"pasador_esfera_{i+1}", "pasador", "frente", pol(93, a), {"t": "pasador", "r": 2.2}, rotI=False, espI=False, capa=6, variante="pasador_esfera", nombre="Pasador del pie de esfera") for i, a in enumerate((100, 260))])
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "escarabajo", 48, capa=7))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "poker", 74, capa=8))
    # encajado
    L.add(base("caja_interior", "caja_interior", "frente", (0, 0), {"t": "caja", "r": 112, "estilo": "bolsillo_antiguo", "colgante": True}, capa=10))
    L.add(base("cristal", "cristal", "frente", (0, 0), {"t": "cristal", "r": 102, "material": "vidrio", "abombado": True}, rotI=False, espI=False, capa=11))
    L.add(base("bisel", "bisel", "frente", (0, 0), {"t": "bisel", "r": 112}, rotI=False, espI=False, capa=12))
    L.add(base("caja_exterior", "caja_exterior", "reverso", (0, 0), {"t": "caja", "r": 122, "estilo": "doble_exterior"}, rot=0, capa=13))
    return L

# ---------------------------------------------------------------- N04 Hamilton 992B
def n04():
    L = Nivel(meta(
        id="n04_hamilton_992b", orden=4, dificultad=4, titulo="La hora del ferrocarril",
        reloj={"nombre": "Reloj de bolsillo ferroviario «Railway Special» de 16 size", "tipo": "Bolsillo, apertura Lépine, puesta en hora por palanca", "ilustracion": "Esquemática propia; sin marcas en esfera ni puentes"},
        casa="Hamilton Watch Company (Lancaster, EE. UU., fundada en 1892)", calibre="Hamilton 992B", anio=1940, epoca="Primera mitad del siglo XX",
        specs={"tamano": "16 size", "rubies": 21, "frecuencia_ah": 18000, "ajustes": "6 posiciones y temperatura", "espiral": "Elinvar Extra", "puesta_en_hora": "Por palanca (lever set)", "funciones": ["Horas", "Minutos", "Segundero pequeño"]},
        historia="Fabricado desde 1940 hasta fines de los años 60, fue uno de los relojes ferroviarios más usados en Estados Unidos, con más de medio millón de unidades.",
        sabias_que=["Las normas ferroviarias exigían al menos 17 rubíes, ajuste a 5 posiciones y un error máximo de unos 30 segundos por semana.",
                    "La hora solo se ajusta abriendo el bisel y sacando una palanca: así nadie la cambiaba por accidente.",
                    "El primer 992B se armó a fines de junio de 1940."],
        cliente={"nombre": "Hernán Fuentes", "perfil": "Maquinista jubilado, San Bernardo", "pedido": "Era de mi padre, que trabajó en la maestranza. Se le cortó la cuerda y la caja está rayada.", "plazo_dias": 5},
        pago_base=85000, reputacion=10, memorice_s=8, prob_espejo=0.2, rot_spawn_max=360,
        orientacion={"corona": 12, "segundero_pequeno": 6},
        preensamblado=["Platina con rubíes", "Piñones de remontoir"],
        mecanicas_nuevas=["pinzas_resortes", "lever_set", "raqueta_micrometrica", "fondo_enroscado"],
        herramientas_requeridas=["abridor_fondos"],
        defectos=["espiral_magnetizado", "muelle_real_roto", "caja_rayada"],
        fuentes=["https://www.kenrockwell.com/watches/hamilton/992b.htm", "https://www.watchfinder.co.uk/articles/review-hamilton-992b-pocket-watch"]))
    C, B, Tt, F, E, P, BAL, CW = (0, 0), (22, -38), (-22, 28), (0, 54), (28, 62), (44, 48), (58, 30), (-4, -64)
    rR = 22
    L.add(palanca("palanca_lever_set", "palanca_lever_set", "frente", (62, 58), [[0, 0], [-12, -4], [-24, -2], [-30, 4]], w=5))
    L.add(tornillo("palanca_lever_set_t", "palanca_lever_set", "frente", (62, 58), cab=1.0, capa=5, nombre="Tornillo de la palanca"))
    L.add(palanca("resorte_palanca", "resorte_palanca_lever_set", "frente", (72, 44), [[0, 0], [-6, -6], [-14, -8]], w=2, curva=True, capa=4))
    L.add(rueda("rueda_puesta_hora", "rueda_puesta_hora", "frente", (10, -46), 9, 20, brazos=0, mat="acero"))
    L.add(rueda("barrilete", "barrilete", "reverso", B, dist(B, C) - 6, 90, brazos=0, capa=1, estilo="barrilete"))
    L.add(rueda("rueda_centro", "rueda_centro", "reverso", C, dist(C, Tt) - 5, 80, pinon=6))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, dist(Tt, F) - 5, 75, pinon=5))
    L.add(rueda("cuarta_rueda", "cuarta_rueda", "reverso", F, dist(F, E) - 4, 80, pinon=5))
    L.add(rueda("rueda_escape", "rueda_escape", "reverso", E, 12, 15, pinon=4, mat="acero", estilo="escape"))
    p, ts = puente(L, "puente_tren", "puente_rodaje", "reverso", ["rueda_centro", "tercera_rueda", "cuarta_rueda", "rueda_escape"], 3, margen=12, nombre="Puente de tren", deco="damasquinado")
    L.add(p); L.add(*ts)
    p, ts = puente(L, "puente_barrilete", "puente_barrilete", "reverso", ["barrilete"], 2, margen=14, extra=[CW, (44, -30)], extra_r=10, deco="damasquinado")
    L.add(p); L.add(*ts)
    L.add(rueda("rochete", "rochete", "reverso", B, rR, 56, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rochete_t", "rochete", "reverso", B, cab=1.6, capa=7, nombre="Tornillo del rochete"))
    L.add(rueda("rueda_corona", "rueda_corona", "reverso", CW, dist(B, CW) - rR, 34, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rueda_corona_t", "rueda_corona", "reverso", CW, cab=1.2, capa=7, nombre="Tornillo de la rueda de corona"))
    L.add(palanca("trinquete", "trinquete", "reverso", (44, -30), [[0, 0], [-8, -6], [-14, -4]], w=4, capa=6))
    L.add(tornillo("trinquete_t", "trinquete", "reverso", (44, -30), cab=1.0, capa=7, nombre="Tornillo del trinquete"))
    L.add(palanca("resorte_trinquete", "resorte_trinquete", "reverso", (54, -20), [[0, 0], [8, -2], [14, 4]], w=2, curva=True, capa=7))
    L.add(ancora("ancora", "reverso", P, BAL))
    p, ts = puente(L, "puente_ancora", "puente_ancora", "reverso", ["ancora"], 2, margen=8, extra=[(56, 62)], extra_r=8, evitar_extra=False)
    L.add(p); L.add(*ts)
    v, ts = volante_con_puente("volante", "volante", "reverso", BAL, 27, [foot(BAL, -24)], extra={"doble_plato": True})
    L.add(v); L.add(*ts)
    L.add(base("raqueta_micrometrica", "raqueta_micrometrica", "reverso", BAL, {"t": "raqueta", "largo": 30, "micrometrica": True}, rot=r1(ang(BAL, C)), capa=8))
    L.add(rueda("canon_minutos", "canon_minutos", "frente", (0, 0), 7, 12, brazos=0, mat="acero", capa=1, estilo="pinon"))
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (24, 12), 17, 40, pinon=8))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 16, 32, brazos=0, capa=3))
    L.add(base("esfera", "esfera_esmalte", "frente", (0, 0), {"t": "esfera", "r": 98, "estilo": "ferroviaria_minutos_numerados", "subseg": [0, 54]}, capa=5))
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "pala", 50, capa=6))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "latigo", 78, capa=7))
    L.add(aguja("segundero_pequeno", "segundero_pequeno", "frente", (0, 54), "baston", 16, rotI=False, capa=7))
    L.add(base("caja", "caja_bolsillo", "frente", (0, 0), {"t": "caja", "r": 116, "estilo": "bolsillo", "colgante": True}, capa=10))
    L.add(base("bisel", "bisel", "frente", (0, 0), {"t": "bisel", "r": 116, "con_cristal": True, "enroscado": True}, rotI=False, espI=False, capa=11, nombre="Bisel con cristal (enroscado)"))
    L.add(base("fondo", "fondo", "reverso", (0, 0), {"t": "fondo", "r": 114, "cierre": "enroscado"}, rotI=False, espI=True, capa=12))
    return L

# ---------------------------------------------------------------- N05 Seiko NH35
def n05():
    L = Nivel(meta(
        id="n05_seiko_nh35", orden=5, dificultad=5, titulo="La buzo del fin de semana",
        reloj={"nombre": "Reloj automático deportivo con fecha", "tipo": "Pulsera, fondo enroscado, 200 m", "ilustracion": "Esquemática propia"},
        casa="Seiko Instruments (Japón)", calibre="Seiko NH35", anio=None, epoca="Década de 2010 – hoy",
        specs={"diametro_mm": 27.4, "rubies": 24, "frecuencia_ah": 21600, "reserva_h": 41, "cuerda": "Automática (Magic Lever) y manual", "stop_segundos": True, "precision": "−20 a +40 s/día", "funciones": ["Horas", "Minutos", "Segundero central", "Fecha"]},
        historia="Versión sin marca del calibre 4R35: robusto, económico y muy usado por marcas independientes. Hereda el sistema de carga Magic Lever.",
        sabias_que=["Seiko presentó el sistema Magic Lever en 1959: una sola palanca de dos uñetas carga en ambos sentidos.",
                    "Para cargar por completo a mano hacen falta decenas de vueltas de corona."],
        cliente={"nombre": "Javiera Muñoz", "perfil": "Buzo recreativa, Quintero", "pedido": "Le entró algo de humedad y el rotor suena raro. ¡Lo necesito para mi próxima inmersión!", "plazo_dias": 4},
        pago_base=95000, reputacion=10, memorice_s=8, prob_espejo=0.25, rot_spawn_max=360,
        orientacion={"corona": 3, "fecha": 3},
        preensamblado=["Platina con rubíes", "Mecanismo de remontoir y puesta en hora"],
        mecanicas_nuevas=["automatico", "palanca_magica", "calendario", "rotor_al_encajar"],
        herramientas_requeridas=["lupa_x5"],
        defectos=["junta_reseca", "rotor_ruidoso", "bisel_rayado"],
        fuentes=["https://calibercorner.com/seiko-caliber-nh35a", "https://museum.seiko.co.jp/en/knowledge/trivia04/"]))
    C, B, Tt, E, P, BAL, CW = (0, 0), (-34, -30), (28, -16), (16, 18), (28, 32), (44, 46), (-64, -8)
    rR = 20
    L.add(rueda("barrilete", "barrilete", "reverso", B, dist(B, C) - 6, 90, brazos=0, capa=1, estilo="barrilete"))
    L.add(rueda("rueda_centro", "rueda_centro", "reverso", C, dist(C, Tt) - 5, 70, pinon=6))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, dist(C, Tt) - 4, 64, pinon=5))
    L.add(rueda("rueda_segundos", "rueda_segundos_central", "reverso", C, dist(C, E) - 4, 60, pinon=4, capa=3))
    L.add(rueda("rueda_escape", "rueda_escape", "reverso", E, 11, 15, pinon=4, mat="acero", estilo="escape"))
    p, ts = puente(L, "puente_barrilete_rodaje", "puente_barrilete_rodaje", "reverso", ["barrilete", "rueda_centro", "tercera_rueda", "rueda_escape"], 3, margen=13, extra=[CW], extra_r=10, mat="niquel", deco="perlado")
    L.add(p); L.add(*ts)
    L.add(rueda("rochete", "rochete", "reverso", B, rR, 54, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rochete_t", "rochete", "reverso", B, cab=1.4, capa=7, nombre="Tornillo del rochete"))
    L.add(rueda("rueda_corona", "rueda_corona", "reverso", CW, dist(B, CW) - rR, 34, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rueda_corona_t", "rueda_corona", "reverso", CW, cab=1.0, capa=7, nombre="Tornillo de la rueda de corona"))
    L.add(ancora("ancora", "reverso", P, BAL))
    p, ts = puente(L, "puente_ancora", "puente_ancora", "reverso", ["ancora"], 1, margen=8, extra=[(18, 44)], extra_r=7, evitar_extra=False, mat="niquel", deco="liso")
    L.add(p); L.add(*ts)
    v, ts = volante_con_puente("volante", "volante", "reverso", BAL, 25, [foot(BAL, 26)])
    L.add(v); L.add(*ts)
    L.add(rueda("rueda_transmision", "rueda_transmision", "reverso", (-24, 22), 15, 48, pinon=5))
    L.add(palanca("palanca_magica", "palanca_magica", "reverso", (-8, 12), [[-10, -12], [0, 0], [10, -12]], w=3, capa=5))
    p, ts = puente(L, "puente_automatico", "puente_automatico", "reverso", ["rueda_transmision", "palanca_magica"], 2, margen=11, extra=[(0, 0)], extra_r=12, mat="niquel", deco="perlado")
    L.add(p); L.add(*ts)
    # frente: minutería y calendario (fecha a las 3)
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (-20, 16), 13, 30, pinon=6))
    L.add(rueda("canon_minutos", "canon_minutos", "frente", (0, 0), 7, 12, brazos=0, mat="acero", capa=1, estilo="pinon"))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 15, 36, brazos=0, capa=3))
    L.add(rueda("rueda_motriz_fecha", "rueda_motriz_fecha", "frente", (-24, -24), dist((0, 0), (-24, -24)) - 15, 48, brazos=0, capa=3, estilo="con_dedo"))
    L.add(base("disco_fecha", "disco_fecha", "frente", (0, 0), {"t": "disco", "r_ext": 94, "r_int": 74, "marcas": 31, "ventana_ang": 90}, rotI=False, espI=True, capa=4))
    L.add(palanca("salteador_fecha", "salteador_fecha", "frente", (60, 46), [[0, 0], [-8, -6], [-18, -6], [-24, -2]], w=2.5, curva=True, capa=5))
    pl = ring_sector(70, 40, 150, 330)
    p, ts = placa("puente_calendario", "puente_calendario", "frente", (0, 0), pl, [pol(56, 190), pol(56, 290)], capa=6)
    L.add(p); L.add(*ts)
    L.add(base("esfera", "esfera", "frente", (0, 0), {"t": "esfera", "r": 98, "estilo": "deportiva_luminiscente", "ventana": {"ang": 90, "tipo": "fecha"}}, capa=7))
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "flecha_luminiscente", 50, capa=8))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "espada_luminiscente", 76, capa=9))
    L.add(aguja("segundero", "segundero", "frente", (0, 0), "piruleta", 84, rotI=False, capa=10))
    caja_pulsera(L, fondo="enroscado", con_anillo=True, rotor="perlado")
    return L

# ---------------------------------------------------------------- N06 ETA 2824-2
def tren_automatico_suizo(L, B, Tt, E, P, BAL, CW, click, RD, RW1, RW2, rR=24, bar_tp="barrilete", cw_izq=True, pie_delta=36, n_tb=2, n_tr=3, pa_extra=None, volante_tp="volante", volante_extra=None):
    C = (0, 0)
    L.add(rueda("barrilete", bar_tp, "reverso", B, dist(B, C) - 6, 90, brazos=0, capa=1, estilo="barrilete"))
    L.add(rueda("rueda_centro", "rueda_centro", "reverso", C, dist(C, Tt) - 5, 70, pinon=6))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, dist(C, Tt) - 4, 64, pinon=5))
    L.add(rueda("rueda_segundos", "rueda_segundos_central", "reverso", C, dist(C, E) - 4, 60, pinon=4, capa=3))
    L.add(rueda("rueda_escape", "rueda_escape", "reverso", E, 11, 15, pinon=4, mat="acero", estilo="escape"))
    p, ts = puente(L, "puente_barrilete", "puente_barrilete", "reverso", ["barrilete"], n_tb, margen=13, extra=[CW, click], extra_r=9)
    L.add(p); L.add(*ts)
    p, ts = puente(L, "puente_rodaje", "puente_rodaje", "reverso", ["rueda_centro", "tercera_rueda", "rueda_escape"], n_tr, margen=11)
    L.add(p); L.add(*ts)
    L.add(rueda("rochete", "rochete", "reverso", B, rR, 60, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rochete_t", "rochete", "reverso", B, cab=1.6, capa=7, nombre="Tornillo del rochete"))
    L.add(rueda("rueda_corona", "rueda_corona", "reverso", CW, dist(B, CW) - rR, 34, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rueda_corona_t", "rueda_corona", "reverso", CW, cab=1.2, rosca="izquierda" if cw_izq else "derecha", capa=7, nombre="Tornillo de la rueda de corona" + (" (rosca izquierda)" if cw_izq else "")))
    L.add(palanca("trinquete", "trinquete", "reverso", click, [[0, 0], [-6, -6], [-12, -6]], w=4, capa=6, nombre="Trinquete con resorte integrado"))
    L.add(ancora("ancora", "reverso", P, BAL))
    p, ts = puente(L, "puente_ancora", "puente_ancora", "reverso", ["ancora"], 1, margen=8, extra=[pa_extra] if pa_extra else [], extra_r=7, evitar_extra=False)
    L.add(p); L.add(*ts)
    if volante_tp == "volante_libre":
        L.add(base("volante", "volante_libre", "reverso", BAL, {"t": "volante", "r": 27, "brazos": 2, "espiral": "breguet", "microstella": 4, "mat": "glucydur"}, rotI=False, espI=True, capa=6))
        f1, f2 = foot(BAL, -40, 84), foot(BAL, 40, 84)
        pc = decimate(hull(circle_pts(BAL, 11) + circle_pts(f1, 9) + circle_pts(f2, 9)))
        cc = centroid(pc)
        L.add(base("puente_volante", "puente_volante_doble", "reverso", cc, {"t": "puente", "poly": loc(pc, cc), "mat": "rodio", "deco": "cotes", "rubies": loc([BAL], cc), "agujeros": loc([f1, f2], cc)}, capa=7, cubre=["volante"]))
        L.add(tornillo("puente_volante_t1", "puente_volante", "reverso", f1, cab=1.2, capa=8, nombre="Tornillo del puente de volante"),
              tornillo("puente_volante_t2", "puente_volante", "reverso", f2, cab=1.2, capa=8, nombre="Tornillo del puente de volante"))
    else:
        v, ts = volante_con_puente("volante", volante_tp, "reverso", BAL, 27, [foot(BAL, pie_delta)], extra=volante_extra)
        L.add(v); L.add(*ts)
    L.add(rueda("rueda_reduccion", "rueda_reduccion", "reverso", RD, 14, 40, pinon=6))
    L.add(rueda("rueda_inversora_1", "rueda_inversora", "reverso", RW1, 11, 32, brazos=0, mat="rojo" if volante_tp == "volante_libre" else "laton", estilo="inversora", variante="rueda_inversora"),
          rueda("rueda_inversora_2", "rueda_inversora", "reverso", RW2, 11, 32, brazos=0, mat="rojo" if volante_tp == "volante_libre" else "laton", estilo="inversora", variante="rueda_inversora"))

def calendario(L, dias=False, corrector=True, n_t=3, salto_instantaneo=False, ventana_ang=90, esfera_estilo="baston_moderno", agujas=("dauphine", "dauphine", "fina"), tornillos_pie=False, contadores=None, subseg=None, crono=False):
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (-20, 16), 13, 30, pinon=6))
    L.add(rueda("canon_minutos", "canon_minutos", "frente", (0, 0), 7, 12, brazos=0, mat="acero", capa=1, estilo="pinon"))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 15, 36, brazos=0, capa=3))
    if salto_instantaneo:
        L.add(rueda("rueda_motriz_fecha", "rueda_salto_instantaneo", "frente", (-24, -24), dist((0, 0), (-24, -24)) - 15, 48, brazos=0, capa=3, estilo="con_dedo"))
        L.add(palanca("resorte_salto_instantaneo", "resorte_salto_instantaneo", "frente", (-50, -28), [[0, 0], [10, -8], [20, -8], [26, 0]], w=2, curva=True, capa=4))
    else:
        L.add(rueda("rueda_motriz_fecha", "rueda_motriz_fecha", "frente", (-24, -24), dist((0, 0), (-24, -24)) - 15, 48, brazos=0, capa=3, estilo="con_dedo"))
    if corrector:
        L.add(rueda("corrector_fecha", "corrector_fecha", "frente", (54, -30), 8, 16, brazos=0, mat="acero", capa=3))
    L.add(base("disco_fecha", "disco_fecha", "frente", (0, 0), {"t": "disco", "r_ext": 94, "r_int": 74, "marcas": 31, "ventana_ang": ventana_ang}, rotI=False, espI=True, capa=4))
    L.add(palanca("salteador_fecha", "salteador_fecha", "frente", (60, 46), [[0, 0], [-8, -6], [-18, -6], [-24, -2]], w=2.5, curva=True, capa=5))
    if dias:
        L.add(rueda("estrella_dias", "estrella_dias", "frente", (0, 0), 20, 7, brazos=0, mat="acero", capa=5, estilo="estrella"))
        L.add(base("disco_dias", "disco_dias", "frente", (0, 0), {"t": "disco", "r_ext": 72, "r_int": 52, "marcas": 7, "ventana_ang": ventana_ang}, rotI=False, espI=True, capa=6))
        L.add(palanca("salteador_dias", "salteador_dias", "frente", (-44, 48), [[0, 0], [8, -6], [16, -6], [22, -2]], w=2.5, curva=True, capa=6))
    pl = ring_sector(70 if not dias else 50, 34, 150, 330)
    tw = [pol(60 if not dias else 44, a) for a in ((170, 250, 320) if n_t == 3 else (190, 290))]
    p, ts = placa("puente_calendario", "puente_calendario", "frente", (0, 0), pl, tw, capa=7)
    L.add(p); L.add(*ts)
    fe = {"t": "esfera", "r": 98, "estilo": esfera_estilo, "ventana": {"ang": ventana_ang, "tipo": "dia_fecha" if dias else "fecha"}}
    if contadores: fe["contadores"] = contadores
    if subseg: fe["subseg"] = subseg
    L.add(base("esfera", "esfera", "frente", (0, 0), fe, capa=8))
    if tornillos_pie:
        L.add(tornillo("esfera_t1", "esfera", "reverso", pol(95, 100), cab=0.8, giros=1.5, capa=9, nombre="Tornillo del pie de esfera"),
              tornillo("esfera_t2", "esfera", "reverso", pol(95, 260), cab=0.8, giros=1.5, capa=9, nombre="Tornillo del pie de esfera"))

def n06():
    L = Nivel(meta(
        id="n06_eta_2824_2", orden=6, dificultad=6, titulo="El automático de todos los días",
        reloj={"nombre": "Reloj automático suizo de tres agujas con fecha", "tipo": "Pulsera, fondo enroscado", "ilustracion": "Esquemática propia"},
        casa="ETA (Suiza, Swatch Group); hereda un diseño de Eterna", calibre="ETA 2824-2", anio=1982, epoca="Desde 1971 (versión -2 desde 1982)",
        specs={"diametro_mm": 25.6, "lineas": "11½'''", "alto_mm": 4.6, "rubies": 25, "frecuencia_ah": 28800, "reserva_h": 38, "cuerda": "Automática bidireccional y manual", "stop_segundos": True, "funciones": ["Horas", "Minutos", "Segundero central", "Fecha con corrección rápida"]},
        historia="Uno de los movimientos automáticos más usados de la historia: robusto, preciso y fácil de servir. Su volante grande está a las 12 visto desde el fondo.",
        sabias_que=["Se fabricó en cuatro calidades con el mismo tamaño y número de rubíes.",
                    "Existen movimientos equivalentes de otros fabricantes basados en su diseño."],
        cliente={"nombre": "Andrés Lagos", "perfil": "Ingeniero en minería, Antofagasta", "pedido": "Atrasa y la fecha a veces queda a medias. Lo uso todos los días en faena.", "plazo_dias": 5},
        pago_base=120000, reputacion=12, memorice_s=7, rot_spawn_max=360,
        orientacion={"corona": 3, "fecha": 3, "volante_reverso": 12},
        preensamblado=["Platina con rubíes", "Mecanismo de remontoir, puesta en hora y stop"],
        mecanicas_nuevas=["ruedas_inversoras", "corrector_fecha", "bridas_encajado", "alineacion_pivotes"],
        herramientas_requeridas=["pinzas_antimagneticas"],
        defectos=["suciedad_general", "salteador_fatigado", "desregulado"],
        fuentes=["https://wiki.grail-watch.com/index.php/ETA_2824-2", "https://monochrome-watches.com/the-history-of-the-eta-2824-the-mundane-calibre-that-shaped-the-industry/", "https://ranfft.org/caliber/4186-ETA-2824"]))
    tren_automatico_suizo(L, B=(-30, 30), Tt=(32, 12), E=(16, -18), P=(10, -36), BAL=(0, -58), CW=(-64, 8), click=(-52, 42), RD=(-48, 54), RW1=(-26, -34), RW2=(-44, -14), pa_extra=(24, -44))
    p, ts = puente(L, "puente_automatico", "puente_automatico", "reverso", ["rueda_reduccion", "rueda_inversora_1", "rueda_inversora_2"], 2, margen=11, extra=[(0, 0)], extra_r=12)
    L.add(p); L.add(*ts)
    calendario(L, corrector=True, n_t=3)
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "dauphine", 50, capa=9))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "dauphine", 76, capa=10))
    L.add(aguja("segundero", "segundero", "frente", (0, 0), "fina", 84, rotI=False, capa=11))
    caja_pulsera(L, fondo="enroscado", con_anillo=False, bridas=True, rotor="cotes")
    return L

# ---------------------------------------------------------------- N07 Hamilton H-40
def n07():
    L = Nivel(meta(
        id="n07_hamilton_h40", orden=7, dificultad=7, titulo="Ochenta horas de vuelo",
        reloj={"nombre": "Reloj de piloto automático con día y fecha (tipo Khaki Aviation Pilot Day Date)", "tipo": "Pulsera 42 mm, fondo de exhibición", "ilustracion": "Esquemática propia; sin copiar esfera ni caja del modelo"},
        casa="Hamilton (nacida en Lancaster, EE. UU.; hoy en Biel, Suiza)", calibre="Hamilton H-40", anio=None, epoca="Actual",
        specs={"base": "Familia ETA 2834-2, modificada", "rubies": 25, "frecuencia_ah": 21600, "reserva_h": 80, "cuerda": "Automática y manual", "funciones": ["Horas", "Minutos", "Segundero central", "Día", "Fecha"]},
        historia="Calibre automático moderno que baja la frecuencia y usa un muelle más largo para llegar a 80 horas: te lo sacas el viernes y sigue andando el lunes.",
        sabias_que=["Bajar de 28.800 a 21.600 alternancias por hora reduce el consumo del escape y alarga la reserva.",
                    "La misma casa fabricó relojes ferroviarios en EE. UU. y hoy produce en Suiza."],
        cliente={"nombre": "Capitana Fernanda Rojas", "perfil": "Piloto de aerolínea, Santiago", "pedido": "Después de un vuelo empezó a adelantar muchísimo. Y la correa ya no da más.", "plazo_dias": 4},
        pago_base=150000, reputacion=14, memorice_s=7, rot_spawn_max=360,
        orientacion={"corona": 3, "dia_fecha": 3},
        preensamblado=["Platina con rubíes", "Mecanismo de remontoir y puesta en hora"],
        mecanicas_nuevas=["dia_fecha", "reserva_80h"],
        herramientas_requeridas=["desmagnetizador"],
        defectos=["espiral_magnetizado", "correa_gastada", "cristal_zafiro_astillado"],
        fuentes=["https://watchbase.com/eta/caliber/h-40", "https://www.hourstriker.com/database/hamilton-khaki-aviation-pilot-day-date-auto-h64615135-7177"]))
    tren_automatico_suizo(L, B=(-30, 30), Tt=(32, 12), E=(16, -18), P=(10, -36), BAL=(0, -58), CW=(-64, 8), click=(-52, 42), RD=(-48, 54), RW1=(-26, -34), RW2=(-44, -14), bar_tp="barrilete_80h", pa_extra=(24, -44))
    p, ts = puente(L, "puente_automatico", "puente_automatico", "reverso", ["rueda_reduccion", "rueda_inversora_1", "rueda_inversora_2"], 2, margen=11, extra=[(0, 0)], extra_r=12)
    L.add(p); L.add(*ts)
    calendario(L, dias=True, corrector=True, n_t=3, esfera_estilo="piloto_arabigo")
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "espada_luminiscente", 50, capa=9))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "espada_luminiscente", 78, capa=10))
    L.add(aguja("segundero", "segundero", "frente", (0, 0), "fina", 84, rotI=False, capa=11))
    caja_pulsera(L, fondo="exhibicion", con_anillo=False, bridas=True, rotor="grabado")
    return L

# ---------------------------------------------------------------- N08 Rolex 3135
def n08():
    L = Nivel(meta(
        id="n08_rolex_3135", orden=8, dificultad=8, titulo="Presión de las profundidades",
        reloj={"nombre": "Reloj de buceo automático de alta gama con fecha", "tipo": "Pulsera, caja hermética con corona enroscada", "ilustracion": "Esquemática propia; sin reproducir el diseño de caja, bisel ni esfera de ningún modelo"},
        casa="Rolex (Ginebra, Suiza)", calibre="Rolex 3135", anio=1988, epoca="Fines del siglo XX",
        specs={"diametro_mm": 28.5, "lineas": "12½'''", "alto_mm": 6.0, "rubies": 31, "frecuencia_ah": 28800, "reserva_h": 48, "cuerda": "Automática bidireccional y manual", "stop_segundos": True, "certificacion": "Cronómetro (COSC)", "funciones": ["Horas", "Minutos", "Segundero central", "Fecha instantánea con corrección rápida"]},
        historia="Calibre presentado en 1988 y usado durante décadas en relojes de buceo y de vestir. Puente de volante de doble apoyo, volante libre regulado con tuercas Microstella y espiral con curva Breguet.",
        sabias_que=["Sus ruedas inversoras son rojas: una seña de identidad de la casa.",
                    "Para regular, se giran por igual las tuercas Microstella opuestas; si no, el volante pierde el equilibrio.",
                    "La familia 3100 estrenó el puente de volante de doble apoyo en lugar del coq de un solo brazo."],
        cliente={"nombre": "Comandante Ricardo Pérez (R)", "perfil": "Buzo táctico retirado de la Armada, Talcahuano", "pedido": "No lo he servido en 15 años. Quiero que vuelva a ser cronómetro y que selle como el primer día.", "plazo_dias": 7},
        pago_base=260000, reputacion=18, memorice_s=6, rot_spawn_max=360,
        orientacion={"corona": 3, "fecha": 3, "volante_reverso": 6},
        preensamblado=["Platina con rubíes", "Mecanismo de remontoir, puesta en hora y stop"],
        mecanicas_nuevas=["volante_libre_microstella", "puente_doble_apoyo", "salto_instantaneo", "tornillos_pie_esfera", "cronometro"],
        herramientas_requeridas=["cronocomparador", "llave_fondos_hermeticos", "llave_microstella"],
        defectos=["aceite_seco", "fuera_de_ritmo", "junta_reseca", "caja_rayada"],
        fuentes=["https://reference.grail-watch.com/movement/rolex-3135/", "https://calibercorner.com/rolex-caliber-3135/", "https://wiki.grail-watch.com/index.php/Rolex_3135"]))
    tren_automatico_suizo(L, B=(-32, -28), Tt=(30, -20), E=(14, 20), P=(10, 38), BAL=(0, 60), CW=(-66, -4), click=(-50, -54), RD=(-12, -54), RW1=(16, -26), RW2=(-8, -30), rR=22, n_tb=2, n_tr=2, pa_extra=(24, 46), volante_tp="volante_libre")
    p, ts = puente(L, "puente_automatico", "puente_automatico", "reverso", ["rueda_reduccion", "rueda_inversora_1", "rueda_inversora_2"], 3, margen=11, extra=[(0, -8)], extra_r=12)
    L.add(p); L.add(*ts)
    calendario(L, corrector=True, n_t=3, salto_instantaneo=True, esfera_estilo="buceo_indices_generico", tornillos_pie=True)
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "flecha_luminiscente", 50, capa=9))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "espada_luminiscente", 78, capa=10))
    L.add(aguja("segundero", "segundero", "frente", (0, 0), "piruleta", 84, rotI=False, capa=11))
    caja_pulsera(L, fondo="enroscado_hermetico", con_anillo=False, bridas=True, rotor="grabado", estilo="hermetica")
    return L

# ---------------------------------------------------------------- N09 Tourbillon
def n09():
    L = Nivel(meta(
        id="n09_tourbillon", orden=9, dificultad=9, titulo="El torbellino",
        reloj={"nombre": "Reloj de vestir con tourbillon de un minuto", "tipo": "Pulsera, apertura en la esfera a las 6, fondo de exhibición", "ilustracion": "Esquemática propia"},
        casa="Invención de Abraham-Louis Breguet (patente de 1801); pieza contemporánea de alta relojería", calibre="Tourbillon de un minuto, cuerda manual (arquitectura didáctica)", anio=1801, epoca="Invento de 1801 · ejecución contemporánea",
        specs={"rubies": 21, "frecuencia_ah": 21600, "reserva_h": 72, "cuerda": "Manual", "jaula": "1 vuelta por minuto", "funciones": ["Horas", "Minutos", "Segundos en la jaula"], "nota": "Valores de una pieza contemporánea típica, no de un calibre específico."},
        historia="El tourbillon monta escape y volante dentro de una jaula que gira: así reparte en todas direcciones los errores que la gravedad provoca cuando el reloj está vertical.",
        sabias_que=["Breguet patentó el tourbillon en París en 1801.",
                    "La jaula completa puede pesar menos de medio gramo."],
        cliente={"nombre": "Casa de subastas «Martillo Austral»", "perfil": "Subastas de relojería, Punta Arenas", "pedido": "Necesitamos servicio completo y certificado de marcha antes del remate de invierno.", "plazo_dias": 10},
        pago_base=380000, reputacion=22, memorice_s=6, prob_espejo=0.3, rot_spawn_max=360,
        orientacion={"corona": 3, "tourbillon": 6},
        preensamblado=["Platina con rubíes"],
        mecanicas_nuevas=["jaula_tourbillon", "zoom_lupa_x10", "submodulo"],
        herramientas_requeridas=["lupa_x10", "kit_tourbillon"],
        defectos=["eje_volante_roto", "suciedad_general", "desregulado"],
        fuentes=[]))
    # frente: remontoir completo
    L.add(rueda("pinon_remontoir", "pinon_remontoir", "frente", (62, 0), 5, 14, brazos=0, mat="acero", capa=2, estilo="pinon"))
    L.add(rueda("pinon_corredizo", "pinon_corredizo", "frente", (48, 0), 5, 12, brazos=0, mat="acero", capa=2, estilo="corredizo"))
    L.add(base("tija", "tija", "frente", (72, 0), {"t": "tija", "largo": 54}, rot=90, capa=3))
    L.add(palanca("tirete", "tirete", "frente", (40, -18), [[0, 0], [0, -10], [8, -18], [18, -18]], capa=4))
    L.add(palanca("bascula", "bascula", "frente", (36, 16), [[0, 0], [10, -6], [16, -14]], capa=4))
    pb = [(22, -36), (52, -40), (62, -20), (60, 24), (44, 32), (24, 22)]
    p, ts = placa("brida_tirete", "brida_tirete", "frente", (42, -6), pb, [(30, -26), (32, 16)], capa=5, deco="perlage")
    L.add(p); L.add(*ts)
    L.add(rueda("rueda_puesta_hora", "rueda_puesta_hora", "frente", (24, 34), 9, 20, brazos=0, mat="acero", capa=3))
    # reverso: tren + jaula
    C, B, Tt, TB, CW, click = (0, 0), (-30, -34), (22, 30), (0, 56), (-62, -10), (-58, -44)
    rR = 24
    L.add(rueda("barrilete", "barrilete", "reverso", B, dist(B, C) - 6, 90, brazos=0, capa=1, estilo="barrilete"))
    L.add(rueda("rueda_centro", "rueda_centro", "reverso", C, dist(C, Tt) - 5, 80, pinon=6))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, dist(Tt, TB) - 6, 75, pinon=5))
    L.add(rueda("rueda_fija", "rueda_fija_tourbillon", "reverso", TB, 30, 90, brazos=0, capa=2, estilo="fija"))
    rf1, rf2 = pol(27, 215), pol(27, 145)
    L.add(tornillo("rueda_fija_t1", "rueda_fija", "reverso", (TB[0] + rf1[0], TB[1] + rf1[1]), cab=0.8, capa=3, nombre="Tornillo de la rueda fija"),
          tornillo("rueda_fija_t2", "rueda_fija", "reverso", (TB[0] + rf2[0], TB[1] + rf2[1]), cab=0.8, capa=3, nombre="Tornillo de la rueda fija"))
    p, ts = puente(L, "puente_barrilete", "puente_barrilete", "reverso", ["barrilete"], 2, margen=13, extra=[CW, click], extra_r=9, deco="cotes")
    L.add(p); L.add(*ts)
    p, ts = puente(L, "puente_rodaje", "puente_rodaje", "reverso", ["rueda_centro", "tercera_rueda"], 2, margen=11, deco="cotes")
    L.add(p); L.add(*ts)
    L.add(rueda("rochete", "rochete", "reverso", B, rR, 60, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rochete_t", "rochete", "reverso", B, cab=1.6, capa=7, nombre="Tornillo del rochete"))
    L.add(rueda("rueda_corona", "rueda_corona", "reverso", CW, dist(B, CW) - rR, 34, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rueda_corona_t", "rueda_corona", "reverso", CW, cab=1.2, rosca="izquierda", capa=7, nombre="Tornillo de la rueda de corona (rosca izquierda)"))
    L.add(palanca("trinquete", "trinquete", "reverso", click, [[0, 0], [6, -6], [12, -4]], w=4, capa=6))
    L.add(palanca("resorte_trinquete", "resorte_trinquete", "reverso", (click[0] - 8, click[1] + 10), [[0, 0], [-6, -6], [-8, -14]], w=2, curva=True, capa=7))
    mod = "jaula_tourbillon"
    L.add(base("jaula_inferior", "jaula_inferior", "reverso", TB, {"t": "jaula", "r": 22, "parte": "inferior"}, rot=0, capa=3, modulo=mod))
    L.add(rueda("rueda_escape", "rueda_escape", "reverso", (TB[0] + 12, TB[1] - 4), 6, 15, pinon=3, mat="acero", estilo="escape", capa=4, modulo=mod))
    L.add(ancora("ancora", "reverso", (TB[0] + 6, TB[1] + 6), (TB[0], TB[1]), capa=4, modulo=mod))
    L.add(base("puente_ancora_jaula", "puente_ancora_jaula", "reverso", (TB[0] + 8, TB[1] + 8), {"t": "palanca", "pts": [[-6, 0], [6, 0]], "w": 5, "mat": "acero"}, rot=0, capa=5, modulo=mod))
    L.add(tornillo("puente_ancora_jaula_t", "puente_ancora_jaula", "reverso", (TB[0] + 12, TB[1] + 8), cab=0.6, giros=1.5, capa=6, modulo=mod, nombre="Tornillo del puente del áncora de la jaula"))
    cols = [(TB[0] + x, TB[1] + y) for x, y in (pol(19, 0), pol(19, 120), pol(19, 240))]
    L.add(*[base(f"columna_jaula_{i+1}", "columna_jaula", "reverso", c, {"t": "columna", "r": 2.2}, rotI=False, espI=False, capa=5, modulo=mod, variante="columna_jaula") for i, c in enumerate(cols)])
    L.add(base("volante", "volante_jaula", "reverso", TB, {"t": "volante", "r": 16, "brazos": 3, "espiral": "plana", "mat": "glucydur"}, rotI=False, espI=True, capa=6, modulo=mod))
    L.add(base("jaula_superior", "jaula_superior", "reverso", TB, {"t": "jaula", "r": 22, "parte": "superior", "brazos": 3}, rot=0, capa=7, modulo=mod))
    L.add(*[tornillo(f"jaula_superior_t{i+1}", "jaula_superior", "reverso", c, cab=0.6, giros=1.5, capa=8, modulo=mod, nombre="Tornillo de la jaula") for i, c in enumerate(cols)])
    f1, f2 = (-44, 70), (44, 70)
    pc = decimate(hull(circle_pts(TB, 12) + circle_pts(f1, 10) + circle_pts(f2, 10)))
    cc = centroid(pc)
    L.add(base("puente_tourbillon", "puente_tourbillon", "reverso", cc, {"t": "puente", "poly": loc(pc, cc), "mat": "rodio", "deco": "espejo", "rubies": loc([TB], cc), "agujeros": loc([f1, f2], cc)}, capa=9, cubre=["jaula_superior"]))
    L.add(tornillo("puente_tourbillon_t1", "puente_tourbillon", "reverso", f1, cab=1.2, capa=10, nombre="Tornillo del puente del tourbillon"),
          tornillo("puente_tourbillon_t2", "puente_tourbillon", "reverso", f2, cab=1.2, capa=10, nombre="Tornillo del puente del tourbillon"))
    L.add(base("chaton", "chaton_tourbillon", "reverso", TB, {"t": "chaton", "r": 6}, rotI=False, espI=True, capa=11))
    L.add(tornillo("chaton_t1", "chaton", "reverso", (TB[0] - 9, TB[1]), cab=0.6, giros=1.5, capa=12, nombre="Tornillo del chatón"),
          tornillo("chaton_t2", "chaton", "reverso", (TB[0] + 9, TB[1]), cab=0.6, giros=1.5, capa=12, nombre="Tornillo del chatón"))
    # frente
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (-20, 16), 13, 30, pinon=6))
    L.add(rueda("canon_minutos", "canon_minutos", "frente", (0, 0), 7, 12, brazos=0, mat="acero", capa=1, estilo="pinon"))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 15, 36, brazos=0, capa=3))
    L.add(base("esfera", "esfera", "frente", (0, 0), {"t": "esfera", "r": 98, "estilo": "guilloche_romano", "apertura": [0, 56, 26]}, capa=5))
    L.add(tornillo("esfera_t1", "esfera", "reverso", pol(95, 100), cab=0.8, giros=1.5, capa=13, nombre="Tornillo del pie de esfera"),
          tornillo("esfera_t2", "esfera", "reverso", pol(95, 260), cab=0.8, giros=1.5, capa=13, nombre="Tornillo del pie de esfera"))
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), "breguet", 48, capa=6))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), "breguet", 74, capa=7))
    L.add(aguja("aguja_tourbillon", "aguja_tourbillon", "frente", (0, 56), "flecha", 14, rotI=False, capa=8))
    # encajado (sin anillo; con bridas; sin rotor)
    L.add(base("caja", "caja", "frente", (0, 0), {"t": "caja", "r": 116, "estilo": "vestir", "asas": True}, capa=10))
    L.add(base("corona", "corona", "frente", (124, 0), {"t": "corona", "r": 9}, rot=90, rotI=True, espI=False, capa=11))
    b1, b2 = pol(103, 135), pol(103, 315)
    L.add(base("brida_encajado_1", "brida_encajado", "reverso", b1, {"t": "garra", "largo": 14}, rot=r1(ang((0, 0), b1)), capa=10),
          base("brida_encajado_2", "brida_encajado", "reverso", b2, {"t": "garra", "largo": 14}, rot=r1(ang((0, 0), b2)), capa=10))
    L.add(tornillo("brida_encajado_1_t", "brida_encajado_1", "reverso", pol(97, 135), cab=1.0, capa=11, nombre="Tornillo de brida de encajado"),
          tornillo("brida_encajado_2_t", "brida_encajado_2", "reverso", pol(97, 315), cab=1.0, capa=11, nombre="Tornillo de brida de encajado"))
    L.add(base("junta", "junta", "reverso", (0, 0), {"t": "junta", "r": 106}, rotI=False, espI=False, capa=12))
    L.add(base("fondo", "fondo", "reverso", (0, 0), {"t": "fondo", "r": 112, "cierre": "exhibicion"}, rotI=False, espI=True, capa=13))
    return L

# ---------------------------------------------------------------- Cronógrafos (base común)
def base_crono(L, B, Tt, F, E, P, BAL, CW=None, click=None, rR=22, volante_tp="volante", bar_tp="barrilete"):
    C = (0, 0)
    L.add(rueda("barrilete", bar_tp, "reverso", B, dist(B, C) - 6, 90, brazos=0, capa=1, estilo="barrilete"))
    L.add(rueda("rueda_centro", "rueda_centro", "reverso", C, dist(C, Tt) - 5, 80, pinon=6))
    L.add(rueda("tercera_rueda", "tercera_rueda", "reverso", Tt, dist(Tt, F) - 5, 75, pinon=5))
    L.add(rueda("cuarta_rueda", "cuarta_rueda", "reverso", F, dist(F, E) - 4, 80, pinon=5))
    L.add(rueda("rueda_escape", "rueda_escape", "reverso", E, 11, 15, pinon=4, mat="acero", estilo="escape"))
    extra = [p for p in (CW, click) if p]
    a = ang(C, B)
    pies = [] if extra else [pol(80, a - 28), pol(80, a + 28)]
    p, ts = puente(L, "puente_barrilete", "puente_barrilete", "reverso", ["barrilete"], 2, margen=13, extra=extra, extra_r=9, pies=pies)
    L.add(p); L.add(*ts)
    p, ts = puente(L, "puente_rodaje", "puente_rodaje", "reverso", ["tercera_rueda", "cuarta_rueda", "rueda_escape"], 2, margen=11)
    L.add(p); L.add(*ts)
    L.add(rueda("rochete", "rochete", "reverso", B, rR, 56, brazos=0, mat="acero", capa=6, estilo="soleil"))
    L.add(tornillo("rochete_t", "rochete", "reverso", B, cab=1.6, capa=7, nombre="Tornillo del rochete"))
    if CW:
        L.add(rueda("rueda_corona", "rueda_corona", "reverso", CW, dist(B, CW) - rR, 34, brazos=0, mat="acero", capa=6, estilo="soleil"))
        L.add(tornillo("rueda_corona_t", "rueda_corona", "reverso", CW, cab=1.2, rosca="izquierda", capa=7, nombre="Tornillo de la rueda de corona (rosca izquierda)"))
    if click:
        L.add(palanca("trinquete", "trinquete", "reverso", click, [[0, 0], [6, -6], [12, -4]], w=4, capa=6))
        L.add(palanca("resorte_trinquete", "resorte_trinquete", "reverso", (click[0] - 8, click[1] - 8), [[0, 0], [-6, 6], [-8, 14]], w=2, curva=True, capa=7))
    L.add(ancora("ancora", "reverso", P, BAL))
    p, ts = puente(L, "puente_ancora", "puente_ancora", "reverso", ["ancora"], 1, margen=8, extra=[(P[0] + 14, P[1] + 4)], extra_r=7, evitar_extra=False)
    L.add(p); L.add(*ts)
    v, ts = volante_con_puente("volante", volante_tp, "reverso", BAL, 24, [foot(BAL, -30)], extra={"raqueta": True})
    L.add(v); L.add(*ts)

def agujas_crono(L, cont_min, cont_hor, subseg, estilo="baston"):
    L.add(aguja("aguja_contador_horas", "aguja_contador_horas", "frente", cont_hor, "baston", 12, capa=9))
    L.add(aguja("aguja_contador_minutos", "aguja_contador_minutos", "frente", cont_min, "baston", 12, capa=9))
    L.add(aguja("segundero_pequeno", "segundero_pequeno", "frente", subseg, "baston", 12, rotI=False, capa=9))
    L.add(aguja("aguja_horas", "aguja_horas", "frente", (0, 0), estilo, 50, capa=10))
    L.add(aguja("aguja_minutos", "aguja_minutos", "frente", (0, 0), estilo, 76, capa=11))
    L.add(aguja("aguja_crono", "aguja_crono", "frente", (0, 0), "fina", 86, capa=12))

# ---------------------------------------------------------------- N10 Valjoux 7750
def n10():
    L = Nivel(meta(
        id="n10_valjoux_7750", orden=10, dificultad=10, titulo="Contra el reloj",
        reloj={"nombre": "Cronógrafo automático con día y fecha", "tipo": "Pulsera, dos pulsadores, contadores a las 12, 6 y 9", "ilustracion": "Esquemática propia"},
        casa="Valjoux (Vallée de Joux, Suiza); hoy ETA", calibre="Valjoux 7750", anio=1974, epoca="Años 70 (relanzado en los 80)",
        specs={"diametro_mm": 30.0, "lineas": "13¼'''", "alto_mm": 7.9, "rubies": 25, "frecuencia_ah": 28800, "reserva_h": 44, "cuerda": "Automática (rodamiento de bolas) y manual", "mando": "Leva de conmutación y piñón oscilante", "funciones": ["Horas", "Minutos", "Segundero pequeño a las 9", "Cronógrafo 30 min a las 12 y 12 h a las 6", "Día y fecha a las 3"]},
        historia="Diseñado por un joven ingeniero en los años 70 y uno de los primeros movimientos simulados por computador. La crisis del cuarzo casi lo hace desaparecer, pero volvió y se convirtió en el cronógrafo automático más usado.",
        sabias_que=["Usa una leva en lugar de rueda de pilares: más simple de producir en serie.",
                    "Su piñón oscilante se basa en un invento de fines del siglo XIX."],
        cliente={"nombre": "Dra. Paula Vergara", "perfil": "Médica de urgencias, Concepción", "pedido": "Lo uso para tomar el pulso. Ahora el cronógrafo no vuelve a cero y el rotor suena.", "plazo_dias": 7},
        pago_base=300000, reputacion=24, memorice_s=5, prob_espejo=0.3, rot_spawn_max=360,
        orientacion={"corona": 3, "contadores": [12, 6], "segundero_pequeno": 9, "dia_fecha": 3},
        preensamblado=["Platina con rubíes", "Mecanismo de remontoir y puesta en hora"],
        mecanicas_nuevas=["cronografo_leva", "pinon_oscilante", "contadores"],
        herramientas_requeridas=["saca_agujas", "colocador_agujas"],
        defectos=["resorte_martillos_fatigado", "rotor_ruidoso", "suciedad_general"],
        fuentes=["https://www.midowatches.com/en/mido-universe-collectors/mido-chronograph-valjoux.html", "https://teddybaldassarre.com/en-ca/blogs/watches/valjoux-7750", "https://reference.grail-watch.com/movement/eta-7750/amp/"]))
    base_crono(L, B=(-34, 30), Tt=(30, -14), F=(54, 0), E=(60, 26), P=(50, 44), BAL=(34, 62))
    C = (0, 0)
    L.add(rueda("rueda_cronografo", "rueda_cronografo", "reverso", C, 30, 120, brazos=4, capa=8, estilo="fina"))
    L.add(rueda("pinon_oscilante", "pinon_oscilante", "reverso", (34, -8), 8, 24, pinon=4, mat="acero", capa=8))
    L.add(rueda("rueda_intermedia_contador", "rueda_intermedia_contador", "reverso", (-12, -36), 8, 20, brazos=0, mat="acero", capa=8))
    L.add(rueda("rueda_contador_minutos", "rueda_contador_minutos", "reverso", (0, -52), 14, 30, brazos=0, capa=8, estilo="con_corazon"))
    L.add(rueda("rueda_contador_horas", "rueda_contador_horas", "reverso", (0, 50), 14, 30, brazos=0, capa=8, estilo="con_corazon"))
    L.add(base("leva_conmutacion", "leva_conmutacion", "reverso", (-42, -26), {"t": "leva", "largo": 26, "ancho": 10}, rot=30, capa=8))
    L.add(palanca("palanca_mando", "palanca_mando", "reverso", (-56, -4), [[0, 0], [-14, -4], [-26, 0], [-30, 8]], w=5, capa=9))
    L.add(palanca("resorte_palanca_mando", "resorte_palanca_mando", "reverso", (-62, -28), [[0, 0], [6, -8], [16, -10]], w=2, curva=True, capa=10))
    L.add(palanca("freno_cronografo", "freno_cronografo", "reverso", (18, 22), [[0, 0], [10, -4], [18, -2]], w=4, capa=9))
    L.add(palanca("martillo_1", "martillo", "reverso", (-22, -10), [[0, 0], [12, 0], [20, -6], [24, -14]], w=6, capa=9, nombre="Martillo de segundos y minutos"))
    L.add(palanca("martillo_2", "martillo", "reverso", (-20, 34), [[0, 0], [10, 4], [16, 10]], w=6, capa=9, nombre="Martillo de horas"))
    L.add(palanca("resorte_martillos", "resorte_martillos", "reverso", (-38, 14), [[0, 0], [8, -6], [18, -6]], w=2, curva=True, capa=10))
    p, ts = puente(L, "puente_cronografo", "puente_cronografo", "reverso", ["rueda_cronografo", "pinon_oscilante", "rueda_contador_minutos", "rueda_contador_horas"], 3, margen=11, capa=11)
    L.add(p); L.add(*ts)
    L.add(rueda("rueda_transmision_1", "rueda_transmision", "reverso", (-30, -46), 12, 36, pinon=5, capa=12, variante="rueda_transmision"),
          rueda("rueda_transmision_2", "rueda_transmision", "reverso", (-50, -30), 10, 30, pinon=5, capa=12, variante="rueda_transmision"))
    p, ts = puente(L, "puente_automatico", "puente_automatico", "reverso", ["rueda_transmision_1", "rueda_transmision_2"], 2, margen=11, extra=[(0, 0)], extra_r=12, capa=13)
    L.add(p); L.add(*ts)
    calendario(L, dias=True, corrector=False, n_t=2, esfera_estilo="cronografo_tricompax", contadores=[[0, -50], [0, 50]], subseg=[-54, 0])
    agujas_crono(L, (0, -50), (0, 50), (-54, 0))
    caja_pulsera(L, fondo="enroscado", con_anillo=True, rotor="perlado", pulsadores=True, estilo="cronografo")
    return L

# ---------------------------------------------------------------- N11 Omega 321
def n11():
    L = Nivel(meta(
        id="n11_omega_321", orden=11, dificultad=11, titulo="Un cronógrafo para la Luna",
        reloj={"nombre": "Cronógrafo manual de la era espacial con cristal acrílico", "tipo": "Pulsera, dos pulsadores, contadores a las 3 y 6, segundero a las 9", "ilustracion": "Esquemática propia; sin reproducir caja, bisel ni esfera de ningún modelo"},
        casa="Omega (Biel, Suiza), sobre un diseño de Lemania", calibre="Omega 321 (Lemania 2310)", anio=1942, epoca="Años 40 a 60 (reeditado en 2019)",
        specs={"diametro_mm": 27.0, "alto_mm": 6.74, "rubies": 17, "frecuencia_ah": 18000, "reserva_h": 44, "cuerda": "Manual", "mando": "Rueda de pilares y embrague horizontal", "funciones": ["Horas", "Minutos", "Segundero pequeño a las 9", "Cronógrafo 30 min y 12 h"]},
        historia="Nació en 1942 de un proyecto conjunto con Lemania y equipó al cronógrafo que en 1957 inició una línea famosa por las misiones espaciales. Fue reemplazado en 1968 y la casa lo volvió a fabricar en 2019.",
        sabias_que=["Para reeditarlo, se escaneó con tomografía un ejemplar que estuvo en la Luna con el Apolo 17.",
                    "Su cristal acrílico no se astilla en fragmentos filosos, algo importante en una cápsula espacial.",
                    "El mismo diseño base se usó en cronógrafos de varias casas de alta relojería."],
        cliente={"nombre": "Dr. Ignacio Soto", "perfil": "Astrónomo de un observatorio en el desierto de Atacama", "pedido": "El cristal está rayado y tiene una pequeña grieta. El cronógrafo arranca a veces sí y a veces no.", "plazo_dias": 8},
        pago_base=420000, reputacion=28, memorice_s=5, prob_espejo=0.3, rot_spawn_max=360,
        orientacion={"corona": 3, "contadores": [3, 6], "segundero_pequeno": 9},
        preensamblado=["Platina con rubíes"],
        mecanicas_nuevas=["rueda_pilares", "embrague_horizontal", "tornillo_excentrico", "cristal_acrilico_aparte"],
        herramientas_requeridas=["prensa_cristales"],
        defectos=["cristal_acrilico_rayado", "cristal_acrilico_grieta", "aceite_seco", "embrague_desajustado"],
        fuentes=["https://wiki.grail-watch.com/index.php/Lemania_2310", "https://quillandpad.com/?p=47748", "https://www.bobswatches.com/rolex-blog/breaking-news/omega-caliber-321-movement-back.html"]))
    # frente: remontoir completo
    L.add(rueda("pinon_remontoir", "pinon_remontoir", "frente", (62, 0), 5, 14, brazos=0, mat="acero", capa=2, estilo="pinon"))
    L.add(rueda("pinon_corredizo", "pinon_corredizo", "frente", (48, 0), 5, 12, brazos=0, mat="acero", capa=2, estilo="corredizo"))
    L.add(base("tija", "tija", "frente", (72, 0), {"t": "tija", "largo": 54}, rot=90, capa=3))
    L.add(palanca("tirete", "tirete", "frente", (40, -18), [[0, 0], [0, -10], [8, -18], [18, -18]], capa=4))
    L.add(palanca("bascula", "bascula", "frente", (36, 16), [[0, 0], [10, -6], [16, -14]], capa=4))
    pb = [(22, -36), (52, -40), (62, -20), (60, 24), (44, 32), (24, 22)]
    p, ts = placa("brida_tirete", "brida_tirete", "frente", (42, -6), pb, [(30, -26), (32, 16)], capa=5, deco="perlage")
    L.add(p); L.add(*ts)
    L.add(rueda("rueda_puesta_hora", "rueda_puesta_hora", "frente", (24, 34), 9, 20, brazos=0, mat="acero", capa=3))
    base_crono(L, B=(-32, -32), Tt=(30, -18), F=(54, 6), E=(58, 32), P=(46, 48), BAL=(28, 62), CW=(-64, -2), click=(-52, -56), volante_tp="volante_tornillos")
    C = (0, 0)
    L.add(base("rueda_pilares", "rueda_pilares", "reverso", (-40, 22), {"t": "rueda_pilares", "r": 10, "pilares": 7}, rotI=False, espI=True, capa=8))
    L.add(palanca("salteador_rueda_pilares", "salteador_rueda_pilares", "reverso", (-56, 34), [[0, 0], [6, -8], [14, -10]], w=2.5, curva=True, capa=9))
    L.add(rueda("rueda_cronografo", "rueda_cronografo", "reverso", C, 30, 120, brazos=4, capa=8, estilo="fina"))
    L.add(base("palanca_embrague", "palanca_embrague", "reverso", (24, 30), {"t": "palanca", "pts": [[0, 0], [6, -12], [14, -26]], "w": 5, "mat": "acero", "rueda_en": [14, -26], "r_rueda": 8}, rot=0, capa=9))
    L.add(palanca("resorte_embrague", "resorte_embrague", "reverso", (12, 40), [[0, 0], [-6, -6], [-12, -4]], w=2, curva=True, capa=10))
    L.add(tornillo("tornillo_excentrico", "palanca_embrague", "reverso", (30, 20), cab=1.0, giros=0.5, capa=10, tp="tornillo_excentrico", nombre="Tornillo excéntrico del embrague"))
    L.add(palanca("palanca_mando", "palanca_mando", "reverso", (-58, 4), [[0, 0], [-8, -10], [-12, -24]], w=5, capa=9))
    L.add(palanca("resorte_palanca_mando", "resorte_palanca_mando", "reverso", (-66, -16), [[0, 0], [6, -8], [16, -10]], w=2, curva=True, capa=10))
    L.add(palanca("freno_cronografo", "freno_cronografo", "reverso", (16, 16), [[0, 0], [10, -4], [18, -2]], w=4, capa=9))
    L.add(rueda("rueda_intermedia_contador", "rueda_intermedia_contador", "reverso", (-32, -8), 7, 18, brazos=0, mat="acero", capa=8))
    L.add(rueda("rueda_contador_minutos", "rueda_contador_minutos", "reverso", (-48, -10), 13, 30, brazos=0, capa=8, estilo="con_corazon"))
    L.add(rueda("rueda_contador_horas", "rueda_contador_horas", "reverso", (0, 48), 13, 30, brazos=0, capa=8, estilo="con_corazon"))
    L.add(palanca("martillo_1", "martillo", "reverso", (-18, -14), [[0, 0], [-10, 0], [-18, 4], [-24, 2]], w=6, capa=9, nombre="Martillo de segundos y minutos"))
    L.add(palanca("martillo_2", "martillo", "reverso", (-12, 34), [[0, 0], [8, 6], [12, 12]], w=6, capa=9, nombre="Martillo de horas"))
    L.add(palanca("resorte_martillos", "resorte_martillos", "reverso", (-30, 36), [[0, 0], [8, -6], [18, -6]], w=2, curva=True, capa=10))
    p, ts = puente(L, "puente_cronografo", "puente_cronografo", "reverso", ["rueda_cronografo", "rueda_contador_minutos", "rueda_pilares"], 2, margen=11, capa=11)
    L.add(p); L.add(*ts)
    p, ts = puente(L, "puente_contador_horas", "puente_contador_horas", "reverso", ["rueda_contador_horas"], 1, margen=9, extra=[(-14, 62)], extra_r=7, evitar_extra=False, capa=11)
    L.add(p); L.add(*ts)
    L.add(rueda("rueda_minutos", "rueda_minutos", "frente", (-20, 16), 13, 30, pinon=6))
    L.add(rueda("canon_minutos", "canon_minutos", "frente", (0, 0), 7, 12, brazos=0, mat="acero", capa=1, estilo="pinon"))
    L.add(rueda("rueda_horas", "rueda_horas", "frente", (0, 0), 15, 36, brazos=0, capa=3))
    L.add(base("esfera", "esfera", "frente", (0, 0), {"t": "esfera", "r": 98, "estilo": "cronografo_mate", "contadores": [[48, -10], [0, 48]], "subseg": [-54, 6]}, capa=8))
    L.add(tornillo("esfera_t1", "esfera", "reverso", pol(95, 100), cab=0.8, giros=1.5, capa=12, nombre="Tornillo del pie de esfera"),
          tornillo("esfera_t2", "esfera", "reverso", pol(95, 260), cab=0.8, giros=1.5, capa=12, nombre="Tornillo del pie de esfera"))
    agujas_crono(L, (48, -10), (0, 48), (-54, 6))
    L.add(base("anillo_encajado", "anillo_encajado", "reverso", (0, 0), {"t": "anillo", "r_in": 100, "r_out": 108}, rotI=False, espI=False, capa=13))
    L.add(base("caja", "caja_pulsadores", "frente", (0, 0), {"t": "caja", "r": 116, "estilo": "cronografo", "asas": True, "pulsadores": [[r1(x) for x in pol(118, 60)], [r1(x) for x in pol(118, 120)]]}, capa=14))
    L.add(base("cristal", "cristal", "frente", (0, 0), {"t": "cristal", "r": 104, "material": "acrilico", "abombado": True}, rotI=False, espI=False, capa=15))
    L.add(base("bisel", "bisel", "frente", (0, 0), {"t": "bisel", "r": 116}, rotI=False, espI=False, capa=16))
    L.add(base("corona", "corona", "frente", (124, 0), {"t": "corona", "r": 9}, rot=90, rotI=True, espI=False, capa=15))
    L.add(base("junta", "junta", "reverso", (0, 0), {"t": "junta", "r": 106}, rotI=False, espI=False, capa=16))
    L.add(base("fondo", "fondo", "reverso", (0, 0), {"t": "fondo", "r": 112, "cierre": "enroscado"}, rotI=False, espI=True, capa=17))
    return L

# ---------------------------------------------------------------- N12 Zenith El Primero
def n12():
    L = Nivel(meta(
        id="n12_zenith_el_primero", orden=12, dificultad=12, titulo="El primero",
        reloj={"nombre": "Cronógrafo automático de alta frecuencia con fecha, de 1969", "tipo": "Pulsera, tres contadores, fondo de exhibición", "ilustracion": "Esquemática propia; sin reproducir esferas tricolor ni cajas de época"},
        casa="Zenith (Le Locle, Suiza)", calibre="Zenith El Primero 3019 PHC", anio=1969, epoca="1969",
        specs={"diametro_mm_aprox": 29, "alto_mm": 6.5, "rubies": 31, "frecuencia_ah": 36000, "reserva_h": 50, "cuerda": "Automática", "mando": "Rueda de pilares y embrague horizontal", "funciones": ["Horas", "Minutos", "Segundero pequeño a las 9", "Cronógrafo 30 min y 12 h", "Fecha"]},
        historia="Uno de los primeros cronógrafos automáticos, presentado en 1969 y capaz de medir décimas de segundo gracias a sus 5 Hz. En la crisis del cuarzo un relojero escondió herramientas y planos, lo que permitió retomar su producción en los años 80.",
        sabias_que=["«El Primero» significa eso mismo en español: fue bautizado como el primero de su clase.",
                    "A 36.000 alternancias por hora, el volante late 10 veces por segundo.",
                    "Una casa de Ginebra usó una versión modificada, más lenta y sin fecha, en sus cronógrafos de los 90."],
        cliente={"nombre": "Sr. Matthias Keller", "perfil": "Coleccionista suizo de paso por Santiago", "pedido": "Es de 1969 y quiero que vuelva a medir décimas de segundo como el primer día.", "plazo_dias": 10},
        pago_base=520000, reputacion=35, memorice_s=5, prob_espejo=0.3, rot_spawn_max=360,
        orientacion={"corona": 3, "contadores": [3, 6], "segundero_pequeno": 9, "fecha": 4.5},
        preensamblado=["Platina con rubíes", "Mecanismo de remontoir y puesta en hora"],
        mecanicas_nuevas=["alta_frecuencia_5hz", "cronografo_automatico_integrado"],
        herramientas_requeridas=["aceiteras"],
        defectos=["suciedad_general", "aceite_seco", "desregulado", "caja_rayada", "junta_reseca"],
        fuentes=["https://quillandpad.com/2019/12/29/exceptional-movements-in-history-zenith-el-primero-reprise/", "https://www.phillips.com/detail/zenith/182740", "https://en.worldtempus.com/article/zenith-el-primero-saga-8265.html"]))
    base_crono(L, B=(-30, -34), Tt=(30, -16), F=(52, 8), E=(56, 34), P=(42, 48), BAL=(24, 60), CW=(-64, -6), click=(-50, -58))
    C = (0, 0)
    L.add(base("rueda_pilares", "rueda_pilares", "reverso", (-42, 18), {"t": "rueda_pilares", "r": 10, "pilares": 6}, rotI=False, espI=True, capa=8))
    L.add(palanca("salteador_rueda_pilares", "salteador_rueda_pilares", "reverso", (-58, 30), [[0, 0], [6, -8], [14, -10]], w=2.5, curva=True, capa=9))
    L.add(rueda("rueda_cronografo", "rueda_cronografo", "reverso", C, 30, 120, brazos=4, capa=8, estilo="fina"))
    L.add(base("palanca_embrague", "palanca_embrague", "reverso", (22, 30), {"t": "palanca", "pts": [[0, 0], [6, -12], [14, -26]], "w": 5, "mat": "acero", "rueda_en": [14, -26], "r_rueda": 8}, rot=0, capa=9))
    L.add(palanca("resorte_embrague", "resorte_embrague", "reverso", (10, 40), [[0, 0], [-6, -6], [-12, -4]], w=2, curva=True, capa=10))
    L.add(tornillo("tornillo_excentrico", "palanca_embrague", "reverso", (28, 20), cab=1.0, giros=0.5, capa=10, tp="tornillo_excentrico", nombre="Tornillo excéntrico del embrague"))
    L.add(palanca("palanca_mando", "palanca_mando", "reverso", (-60, 2), [[0, 0], [-8, -10], [-12, -24]], w=5, capa=9))
    L.add(palanca("resorte_palanca_mando", "resorte_palanca_mando", "reverso", (-68, -18), [[0, 0], [6, -8], [16, -10]], w=2, curva=True, capa=10))
    L.add(palanca("freno_cronografo", "freno_cronografo", "reverso", (16, 16), [[0, 0], [10, -4], [18, -2]], w=4, capa=9))
    L.add(rueda("rueda_intermedia_contador", "rueda_intermedia_contador", "reverso", (-32, -8), 7, 18, brazos=0, mat="acero", capa=8))
    L.add(rueda("rueda_contador_minutos", "rueda_contador_minutos", "reverso", (-48, -12), 13, 30, brazos=0, capa=8, estilo="con_corazon"))
    L.add(rueda("rueda_contador_horas", "rueda_contador_horas", "reverso", (0, 48), 13, 30, brazos=0, capa=8, estilo="con_corazon"))
    L.add(palanca("martillo_1", "martillo", "reverso", (-18, -16), [[0, 0], [-10, 0], [-18, 4], [-24, 2]], w=6, capa=9, nombre="Martillo de segundos y minutos"))
    L.add(palanca("martillo_2", "martillo", "reverso", (-12, 34), [[0, 0], [8, 6], [12, 12]], w=6, capa=9, nombre="Martillo de horas"))
    L.add(palanca("resorte_martillos", "resorte_martillos", "reverso", (-30, 36), [[0, 0], [8, -6], [18, -6]], w=2, curva=True, capa=10))
    p, ts = puente(L, "puente_cronografo", "puente_cronografo", "reverso", ["rueda_cronografo", "rueda_contador_minutos", "rueda_pilares"], 2, margen=11, capa=11)
    L.add(p); L.add(*ts)
    p, ts = puente(L, "puente_contador_horas", "puente_contador_horas", "reverso", ["rueda_contador_horas"], 1, margen=9, extra=[(-14, 62)], extra_r=7, evitar_extra=False, capa=11)
    L.add(p); L.add(*ts)
    L.add(rueda("rueda_reduccion", "rueda_reduccion", "reverso", (-20, -52), 13, 40, pinon=6, capa=12))
    L.add(rueda("rueda_inversora_1", "rueda_inversora", "reverso", (10, -30), 10, 30, brazos=0, estilo="inversora", capa=12, variante="rueda_inversora"),
          rueda("rueda_inversora_2", "rueda_inversora", "reverso", (-12, -32), 10, 30, brazos=0, estilo="inversora", capa=12, variante="rueda_inversora"))
    p, ts = puente(L, "puente_automatico", "puente_automatico", "reverso", ["rueda_reduccion", "rueda_inversora_1", "rueda_inversora_2"], 2, margen=11, extra=[(0, -8)], extra_r=12, capa=13)
    L.add(p); L.add(*ts)
    calendario(L, dias=False, corrector=True, n_t=2, ventana_ang=135, esfera_estilo="cronografo_tricompax", contadores=[[48, -12], [0, 48]], subseg=[-52, 8], tornillos_pie=True)
    agujas_crono(L, (48, -12), (0, 48), (-52, 8))
    caja_pulsera(L, fondo="exhibicion", con_anillo=False, bridas=True, rotor="grabado", pulsadores=True, estilo="cronografo")
    return L

# ------------------------------------------------------------------ herramientas, repuestos, defectos
HERRAMIENTAS = [
    # id, nombre, precio (0 = inicial), categoría, descripción/efecto en juego
    ("portamovimientos", "Portamovimientos", 0, "banco", "Sujeta el movimiento en el centro de la mesa. Siempre presente."),
    ("destornilladores_basicos", "Juego de destornilladores (5 tamaños)", 0, "atornillar", "Hojas de 0,8 a 2,0 mm. Usar el tamaño equivocado hace patinar el tornillo."),
    ("pinzas_laton", "Pinzas de latón", 0, "pinzas", "Modo pinzas con paso de 2 px por toque. No magnetizan las piezas."),
    ("lupa_x3", "Lupa ×3", 0, "vision", "Zoom de la mesa hasta ×1,5."),
    ("pera_aire", "Pera de aire", 0, "limpieza", "Sopla polvo suelto antes de armar."),
    ("pano_pulir", "Paño de pulir", 0, "pulido", "Pule rayas finas en acrílico y metales blandos (lento)."),
    ("llave_cuerda", "Llave de cuerda antigua", 5000, "especial", "Necesaria para relojes de llave del siglo XVIII."),
    ("cuchilla_fondo", "Cuchilla abre-fondos", 8000, "apertura", "Abre fondos a presión."),
    ("pasta_acrilico", "Pasta para pulir acrílico", 8000, "pulido", "Acelera ×2 el pulido de cristales acrílicos."),
    ("lapiz_fibra", "Lápiz de fibra de vidrio", 6000, "limpieza", "Limpia contactos sulfatados de cuarzo."),
    ("herramienta_pasadores", "Herramienta de pasadores", 9000, "correas", "Cambia correas y brazaletes."),
    ("probador_pilas", "Probador de pilas", 12000, "cuarzo", "Mide la tensión de la pila."),
    ("calibre_pie_metro", "Pie de metro digital", 15000, "medicion", "Mide el diámetro del cristal para pedir el repuesto correcto."),
    ("saca_agujas", "Saca-agujas", 18000, "agujas", "Retira agujas sin marcar la esfera."),
    ("colocador_agujas", "Colocador de agujas", 22000, "agujas", "Presiona agujas a la altura justa (necesario en cronógrafos)."),
    ("lupa_x5", "Lupa ×5", 25000, "vision", "Zoom hasta ×2,5."),
    ("multimetro", "Multímetro", 25000, "cuarzo", "Mide continuidad de la bobina y consumo del circuito."),
    ("resina_uv", "Resina UV y lámpara", 30000, "cristal", "Sella microgrietas en cristales acrílicos (no en mineral ni zafiro)."),
    ("llave_microstella", "Llave Microstella", 30000, "regulacion", "Gira las tuercas del volante libre."),
    ("abridor_fondos", "Abridor de fondos enroscados", 35000, "apertura", "Abre fondos con muescas."),
    ("desmagnetizador", "Desmagnetizador", 40000, "regulacion", "Elimina el magnetismo del espiral."),
    ("manual_tecnico", "Manual técnico de calibres", 40000, "mejora", "Suma 3 s a la vista de armado (memorice)."),
    ("pinzas_antimagneticas", "Pinzas antimagnéticas finas", 45000, "pinzas", "Paso fino de 0,75 px; necesarias para alinear pivotes."),
    ("llave_fondos_hermeticos", "Llave para fondos de caja hermética", 45000, "apertura", "Abre fondos estriados de relojes de buceo."),
    ("aceiteras", "Juego de aceiteras y 4 aceites", 50000, "lubricacion", "Habilita la lubricación con el aceite correcto en cada punto."),
    ("lupa_x10", "Lupa ×10", 55000, "vision", "Zoom hasta ×4; indispensable para la jaula del tourbillon."),
    ("destornilladores_pro", "Destornilladores profesionales (9 tamaños)", 60000, "atornillar", "Suma 0,5 y 0,6 mm; atornilla 30 % más rápido y casi no patina."),
    ("prensa_cristales", "Prensa de cristales", 60000, "cristal", "Coloca cristales nuevos a presión."),
    ("motor_pulido", "Motor de pulido con discos", 110000, "pulido", "Pule acero y metales duros ×3 más rápido."),
    ("limpiadora_ultrasonido", "Limpiadora por ultrasonido", 140000, "limpieza", "Limpia piezas en lote (ciclos de lavado, enjuague y secado)."),
    ("kit_tourbillon", "Kit de tourbillon (soporte y pinzas de jaula)", 180000, "especial", "Permite armar la jaula del tourbillon."),
    ("cronocomparador", "Cronocomparador", 220000, "regulacion", "Muestra marcha (s/día), amplitud (°) y error de ritmo (ms)."),
    ("probador_hermeticidad", "Probador de hermeticidad", 250000, "prueba", "Prueba la caja a presión; +reputación en relojes de buceo."),
]
REPUESTOS = [
    ("muelle_real", "Muelle real", 12000), ("eje_volante", "Eje de volante", 25000),
    ("cristal_acrilico", "Cristal acrílico", 9000), ("cristal_mineral", "Cristal mineral", 12000),
    ("cristal_zafiro", "Cristal de zafiro", 35000), ("cristal_vidrio_antiguo", "Cristal de vidrio abombado", 15000),
    ("junta_fondo", "Junta de fondo", 3000), ("corona_repuesto", "Corona", 15000), ("pila_sr626sw", "Pila SR626SW", 3000),
    ("tornillo_repuesto", "Tornillo", 2000), ("salteador_fecha_rep", "Salteador de fecha", 8000), ("bobina_rep", "Bobina", 10000),
    ("correa_cuero", "Correa de cuero", 12000), ("resorte_martillos_rep", "Resorte de martillos", 9000), ("agujas_rep", "Juego de agujas", 10000),
]
DEFECTOS = {
    # id: (nombre, descripción, efecto, operación (minijuego), herramientas, repuesto)
    "suciedad_general": ("Movimiento sucio", "Aceites viejos y polvo frenan el tren.", "AMPLITUD_BAJA", "limpiar", ["pera_aire"], None),
    "aceite_seco": ("Lubricación agotada", "Los puntos de aceite están secos.", "AMPLITUD_BAJA", "lubricar", ["aceiteras"], None),
    "espiral_magnetizado": ("Espiral magnetizado", "Las espiras se pegan entre sí.", "ADELANTA_MUCHO", "desmagnetizar", ["desmagnetizador"], None),
    "muelle_real_roto": ("Muelle real roto", "El muelle se cortó dentro del barrilete.", "SIN_ENERGIA", "reemplazar_pieza", [], "muelle_real"),
    "eje_volante_roto": ("Eje de volante roto", "Un pivote del eje se quebró por un golpe.", "VOLANTE_QUIETO", "reemplazar_pieza", [], "eje_volante"),
    "pila_agotada": ("Pila agotada", "La pila no tiene carga.", "SIN_ENERGIA", "cambiar_pila", ["probador_pilas"], "pila_sr626sw"),
    "contactos_sulfatados": ("Contactos sulfatados", "Una pila vieja dejó óxido en los contactos.", "SIN_ENERGIA", "limpiar_contactos", ["lapiz_fibra"], None),
    "cristal_mineral_trizado": ("Cristal mineral trizado", "El cristal mineral no se repara: se reemplaza.", "SIN_PROTECCION", "reemplazar_cristal", ["prensa_cristales", "calibre_pie_metro"], "cristal_mineral"),
    "cristal_acrilico_rayado": ("Cristal acrílico rayado", "Rayas finas en la superficie.", "INCOMPLETO", "pulir", ["pano_pulir"], None),
    "cristal_acrilico_grieta": ("Microgrieta en acrílico", "Grieta corta que aún no atraviesa el cristal.", "NO_HERMETICO", "sellar_grieta", ["resina_uv"], None),
    "cristal_zafiro_astillado": ("Zafiro astillado", "El zafiro no se pule ni se sella: se reemplaza.", "SIN_PROTECCION", "reemplazar_cristal", ["prensa_cristales", "calibre_pie_metro"], "cristal_zafiro"),
    "cristal_vidrio_roto": ("Cristal de vidrio roto", "Se reemplaza por uno abombado de época.", "SIN_PROTECCION", "reemplazar_cristal", ["calibre_pie_metro"], "cristal_vidrio_antiguo"),
    "caja_rayada": ("Caja rayada", "Rayas de uso en caja y asas.", "INCOMPLETO", "pulir", ["pano_pulir"], None),
    "bisel_rayado": ("Bisel rayado", "Golpes y rayas en el bisel.", "INCOMPLETO", "pulir", ["pano_pulir"], None),
    "junta_reseca": ("Junta reseca", "La goma perdió elasticidad.", "NO_HERMETICO", "cambiar_junta", [], "junta_fondo"),
    "rotor_ruidoso": ("Rotor ruidoso", "El rodamiento del rotor está seco o gastado.", "ROTOR_RUIDOSO", "lubricar", ["aceiteras"], None),
    "salteador_fatigado": ("Salteador fatigado", "El resorte perdió fuerza.", "FECHA_DESALINEADA", "reemplazar_pieza", [], "salteador_fecha_rep"),
    "desregulado": ("Desregulado", "La marcha diaria está fuera de tolerancia.", "DESREGULADO", "regular", ["cronocomparador"], None),
    "fuera_de_ritmo": ("Fuera de ritmo", "El tic y el tac no son simétricos.", "FUERA_DE_RITMO", "ajustar_ritmo", ["cronocomparador"], None),
    "correa_gastada": ("Correa gastada", "La correa está agrietada.", "INCOMPLETO", "cambiar_correa", ["herramienta_pasadores"], "correa_cuero"),
    "cadena_oxidada": ("Cadena del caracol oxidada", "Óxido entre eslabones: hay que limpiarla y aceitarla con cuidado.", "AMPLITUD_BAJA", "limpiar_cadena", ["pera_aire"], None),
    "esmalte_pelo": ("Pelo en el esmalte", "Grieta capilar en la esfera de esmalte: no tiene arreglo seguro.", "INCOMPLETO", "informar_cliente", [], None),
    "resorte_martillos_fatigado": ("Resorte de martillos fatigado", "Los martillos golpean sin fuerza.", "CRONO_NO_VUELVE_A_CERO", "reemplazar_pieza", [], "resorte_martillos_rep"),
    "embrague_desajustado": ("Embrague desajustado", "El tornillo excéntrico quedó mal ajustado.", "CRONO_NO_ARRANCA", "ajustar_excentrico", [], None),
}
TRABAJOS_RAPIDOS = [
    {"id": "tr_pila", "nombre": "Cambio de pila", "pago": 8000, "requiere": ["cuchilla_fondo"], "minijuego": "cambiar_pila"},
    {"id": "tr_correa", "nombre": "Cambio de correa", "pago": 6000, "requiere": ["herramienta_pasadores"], "minijuego": "cambiar_correa"},
    {"id": "tr_pulido_acrilico", "nombre": "Pulido de cristal acrílico", "pago": 7000, "requiere": ["pano_pulir"], "minijuego": "pulir"},
    {"id": "tr_desmagnetizado", "nombre": "Desmagnetizado", "pago": 6000, "requiere": ["desmagnetizador"], "minijuego": "desmagnetizar"},
    {"id": "tr_hermeticidad", "nombre": "Prueba de hermeticidad", "pago": 10000, "requiere": ["probador_hermeticidad"], "minijuego": "prueba_hermeticidad"},
]

CONFIG = {
    "unidades": {"radio_platina": 100, "eje_y": "hacia abajo", "angulos": "grados, sentido horario desde las 12", "lado_reverso": "vista desde el fondo (puentes)", "lado_frente": "vista desde la esfera", "espejo_entre_lados": "x -> -x"},
    "pistas": {"intervalo_s": 300, "max_acumuladas": 1, "duracion_s": 6, "cuenta_solo_juego_activo": True, "penalizacion_pago": 0.05},
    "memorice": {"min_s": 4, "bonus_manual_s": 3, "usos_gratis_por_nivel": 1, "costo_extra": 2000, "cooldown_s": 60},
    "tolerancias": {"aprendiz": {"pos": 10, "rot": 20, "ayuda_orientacion": True},
                    "oficial": {"pos": 7, "rot": 12, "ayuda_orientacion": True},
                    "maestro": {"pos": 4, "rot": 6, "ayuda_orientacion": False, "tornillos_se_pasan": True, "pivotes_se_rompen": True, "resortes_saltan": True}},
    "giro_por_botones_grados": 15,
    "borde": {"zona_frac": 0.18, "pieza_grande_frac": 0.22, "tamano_min_px": 56, "margen_px": 8},
    "pinzas": {"paso_px": {"pinzas_laton": 2.0, "pinzas_antimagneticas": 0.75}, "retardo_repeticion_ms": 300, "repeticion_ms": 60},
    "tornillo": {"torque_max": 1.2, "factor_tamano_incorrecto": 0.4},
    "dinero_inicial": 20000,
    "moneda": {"codigo": "CLP", "simbolo": "$", "separador_miles": ".", "decimales": 0},
    "pago": {"estrellas": {"1": 1.0, "2": 1.1, "3": 1.25}, "penal_error": 0.01, "penal_dia_atraso": 0.1, "minimo_frac": 0.5, "propina_max": 0.15},
    "estrellas": {"3": "sin pistas extra, ≤ 3 errores y bajo tiempo objetivo", "2": "≤ 2 pistas y ≤ 8 errores", "1": "reloj entregado funcionando"},
    "tiempo_objetivo_s_por_pieza": 25,
    "guardado": {"clave_localstorage": "relojero_save_v1", "autoguardado_s": 15},
}

# ------------------------------------------------------------------ armado y validación
def extent(p):
    f = p["forma"]; t = f["t"]; c = math.hypot(p["x"], p["y"])
    if t in ("rueda",): return c + f["r"]
    if t in ("puente", "placa"):
        return max(math.hypot(p["x"] + x, p["y"] + y) for x, y in f["poly"])
    if t == "volante":
        e = c + f["r"]
        if "puente" in f: e = max(e, max(math.hypot(p["x"] + x, p["y"] + y) for x, y in f["puente"]))
        return e
    if t == "palanca": return max(math.hypot(p["x"] + x, p["y"] + y) for x, y in f["pts"]) + f["w"] / 2
    if t == "tornillo": return c + f["r"]
    return c

ENCAJADO = {"anillo_encajado", "brida_encajado", "caja", "caja_bolsillo", "caja_interior", "caja_exterior", "caja_pulsadores", "cristal", "bisel", "corona", "junta", "fondo", "tija_corona", "esfera", "esfera_esmalte", "rotor", "pasador", "aguja_horas", "aguja_minutos", "segundero", "platina_superior", "tija", "disco_fecha"}

def build():
    niveles = []
    for fn in (n01, n02, n03, n04, n05, n06, n07, n08, n09, n10, n11, n12):
        RESERVADOS.clear()
        L0 = fn()
        for q in L0.items:
            if q["forma"]["t"] == "rueda" and q.get("modulo") is None:
                RESERVADOS.setdefault(q["lado"], []).append((q["x"], q["y"]))
        L = fn()
        RESERVADOS.clear()
        items = L.items
        ids = [p["id"] for p in items]
        assert len(ids) == len(set(ids)), (L.meta["id"], [i for i in ids if ids.count(i) > 1])
        paso_de = {p["id"]: p["paso"] for p in items}
        tipo_de = {p["id"]: p["tipo"] for p in items}
        ENC = ENCAJADO | {"brida_encajado"}
        for p in items:
            exento = p["tipo"] in ENC or (p["tipo"] == "tornillo" and tipo_de.get(p.get("sobre")) in ENC)
            for c in p.get("cubre", []):
                assert c in paso_de and paso_de[c] < p["paso"], (L.meta["id"], p["id"], c)
            if p["tipo"] in ("tornillo", "tornillo_excentrico"):
                s = p["sobre"]
                assert s in paso_de and paso_de[s] <= p["paso"], (L.meta["id"], p["id"], s)
            if not exento and p["forma"]["t"] not in ("tija",):
                e = extent(p)
                assert e <= 101.5, (L.meta["id"], p["id"], round(e, 1))
        # un tornillo de puente/placa no puede caer sobre el eje de otra rueda ni sobre otro tornillo del mismo lado
        for s in items:
            if s["tipo"] != "tornillo" or s["id"].endswith("_t") and s["sobre"] in ("rochete", "rueda_corona", "rotor", "trinquete", "trinquete_armado", "regulador_tompion", "palanca_lever_set", "resorte_tirete", "bobina", "brida_pila", "contrapotenza"):
                continue
            for q in items:
                if q is s or q["lado"] != s["lado"]:
                    continue
                if q["forma"]["t"] in ("rueda", "tornillo") and q.get("modulo") is None and not (q["forma"]["t"] == "tornillo" and q.get("sobre") == s.get("sobre") and False):
                    d = math.hypot(q["x"] - s["x"], q["y"] - s["y"])
                    assert d >= 7, (L.meta["id"], s["id"], "choca con", q["id"], round(d, 1))
        m = dict(L.meta)
        m["total_piezas"] = len(items)
        m["total_pasos"] = L.n
        m["tiempo_objetivo_s"] = len(items) * CONFIG["tiempo_objetivo_s_por_pieza"] + 120
        m["lados_usados"] = sorted(set(p["lado"] for p in items))
        for d in m["defectos"]:
            assert d in DEFECTOS, d
        m["secuencia"] = items
        niveles.append(m)
    counts = [n["total_piezas"] for n in niveles]
    assert counts[0] >= 25, counts
    assert all(b > a for a, b in zip(counts, counts[1:])), counts
    return niveles

def main():
    niveles = build()
    herr = [{"id": i, "nombre": n, "precio": p, "inicial": p == 0, "categoria": c, "efecto": d} for i, n, p, c, d in HERRAMIENTAS]
    hid = {h["id"] for h in herr}
    for n in niveles:
        for h in n["herramientas_requeridas"]:
            assert h in hid, h
    for d in DEFECTOS.values():
        for h in d[4]:
            assert h in hid, h
    out = {
        "meta": {
            "titulo": "Maestro Relojero — catálogo de relojes, calibres y piezas",
            "version": "1.0.0", "idioma": "es", "generado": "2026-10-26",
            "descripcion": "Fuente de verdad para el juego: 12 niveles basados en calibres y tipos históricos reales, con secuencias de armado exactas (pasos), geometría esquemática para dibujar en SVG, síntomas por pieza faltante, defectos de reparación, herramientas y economía.",
            "aviso": "Las marcas y calibres se mencionan con fines descriptivos y educativos. El juego no está afiliado a ninguna marca. Todas las ilustraciones deben ser esquemáticas y propias: sin logotipos, nombres de marca sobre esferas o rotores, ni copias de diseños icónicos de cajas o esferas.",
            "nota_didactica": "Las secuencias siguen la lógica real de armado (de abajo hacia arriba, ruedas antes que su puente, tornillos después del puente, minutería antes que esfera y agujas). Se simplifican algunos subconjuntos que en la práctica se sirven ya armados. No reemplazan el manual técnico del fabricante.",
            "reglas_secuencia": "Las piezas con el mismo número de 'paso' forman un grupo y pueden colocarse en cualquier orden dentro del grupo; los grupos deben completarse en orden estricto. Tornillos y pasadores con la misma 'variante' son intercambiables entre sus agujeros del mismo grupo.",
        },
        "config": CONFIG,
        "efectos": {k: {"prioridad": v[0], "titulo": v[1], "descripcion": v[2]} for k, v in EFECTOS.items()},
        "tiposPieza": T,
        "herramientas": herr,
        "repuestos": [{"id": i, "nombre": n, "precio": p} for i, n, p in REPUESTOS],
        "defectos": {k: {"nombre": v[0], "descripcion": v[1], "efecto": v[2], "operacion": v[3], "herramientas": v[4], "repuesto": v[5]} for k, v in DEFECTOS.items()},
        "trabajosRapidos": TRABAJOS_RAPIDOS,
        "resumenNiveles": [{"orden": n["orden"], "id": n["id"], "titulo": n["titulo"], "calibre": n["calibre"], "casa": n["casa"], "anio": n["anio"], "epoca": n["epoca"], "piezas": n["total_piezas"], "pasos": n["total_pasos"], "pago_base": n["pago_base"], "herramientas_requeridas": n["herramientas_requeridas"], "cliente": n["cliente"]["nombre"]} for n in niveles],
        "niveles": niveles,
    }
    import os
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "niveles"), exist_ok=True)

    def compacto(o):
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"))

    def bonito(o, prof=0, max_prof=2):
        """JSON legible: los primeros niveles con saltos de línea; cada pieza/tipo en una sola línea."""
        pad = "  " * prof
        if prof >= max_prof or not isinstance(o, (dict, list)) or not o:
            return compacto(o)
        if isinstance(o, dict):
            filas = [f'{pad}  {json.dumps(k, ensure_ascii=False)}: {bonito(v, prof + 1, max_prof)}' for k, v in o.items()]
            return "{\n" + ",\n".join(filas) + "\n" + pad + "}"
        filas = [pad + "  " + bonito(v, prof + 1, max_prof) for v in o]
        return "[\n" + ",\n".join(filas) + "\n" + pad + "]"

    base_keys = ["meta", "config", "efectos", "tiposPieza", "herramientas", "repuestos", "defectos", "trabajosRapidos", "resumenNiveles"]
    base_out = {k: out[k] for k in base_keys}
    base_out["meta"] = dict(out["meta"], archivos_niveles=[f"niveles/{n['id']}.json" for n in niveles])
    with open(os.path.join(OUT, "catalogo_base.json"), "w", encoding="utf-8") as fh:
        fh.write(bonito(base_out) + "\n")
    for n in niveles:
        with open(os.path.join(OUT, "niveles", f"{n['id']}.json"), "w", encoding="utf-8") as fh:
            fh.write(bonito(n, 0, 2) + "\n")
    with open(os.path.join(OUT, "catalogo_completo.json"), "w", encoding="utf-8") as fh:
        fh.write(bonito(out, 0, 3) + "\n")
    for r in out["resumenNiveles"]:
        print(f"{r['orden']:>2}  {r['calibre']:<45} piezas={r['piezas']:>3}  pasos={r['pasos']:>3}  pago={r['pago_base']}")
    print("tipos:", len(T), " herramientas:", len(herr), " defectos:", len(DEFECTOS))

if __name__ == "__main__":
    main()
