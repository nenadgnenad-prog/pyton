# Zmija 3D - zmija u 3D svijetu jede jabuke, a od lubenice se cijela napuhne
# Kontrole:
#   Strelice ili W A S D - skretanje
#   R   - nova igra
#   Esc - izlaz

import random

from ursina import *

app = Ursina(title="Zmija 3D", borderless=False, development_mode=False)

POLJE = 16          # ploca je POLJE x POLJE kockica
KORAK = 0.16        # sekundi po koraku (manje = brze)
NAPUHNUTA_TRAJE = 5 # sekundi koliko je zmija napuhnuta

window.color = color.rgb32(120, 190, 240)
Sky(color=color.rgb32(150, 210, 255))

# Ploca - sahovnica od dvije nijanse trave
for x in range(POLJE):
    for z in range(POLJE):
        nijansa = color.rgb32(110, 190, 80) if (x + z) % 2 == 0 else color.rgb32(95, 170, 65)
        Entity(model="cube", color=nijansa, position=(x, -0.5, z), scale=(1, 0.2, 1))

# Ograda oko ploce
for i in range(-1, POLJE + 1):
    for pos in ((i, 0, -1), (i, 0, POLJE), (-1, 0, i), (POLJE, 0, i)):
        Entity(model="cube", color=color.rgb32(140, 95, 55), position=pos, scale=(1, 0.6, 1), y=-0.2)

# Kamera gleda ploču koso odozgo
camera.position = (POLJE / 2 - 0.5, 40, -5)
camera.look_at(Vec3(POLJE / 2 - 0.5, 0, POLJE / 2 - 0.5))

ZELENA = color.rgb32(60, 170, 60)
ZELENA2 = color.rgb32(90, 200, 70)


class Dio(Entity):
    """Jedan dio tijela zmije."""

    def __init__(self, polje, glava=False):
        super().__init__(model="sphere", position=Vec3(polje[0], 0.1, polje[1]))
        self.polje = polje
        self.glava = glava
        if glava:
            self.color = color.rgb32(40, 140, 40)
            # oci i jezik
            for strana in (-0.2, 0.2):
                Entity(parent=self, model="sphere", color=color.white, scale=0.3, position=(strana, 0.25, 0.3))
                Entity(parent=self, model="sphere", color=color.black, scale=0.15, position=(strana, 0.3, 0.42))
            Entity(parent=self, model="cube", color=color.red, scale=(0.08, 0.02, 0.35), position=(0, 0, 0.6))


class Hrana(Entity):
    def __init__(self, vrsta, polje):
        self.vrsta = vrsta
        self.polje = polje
        if vrsta == "jabuka":
            super().__init__(model="sphere", color=color.rgb32(220, 30, 30), scale=0.7,
                             position=Vec3(polje[0], 0.05, polje[1]))
            Entity(parent=self, model="cube", color=color.rgb32(90, 60, 30), scale=(0.08, 0.35, 0.08), y=0.55)
            Entity(parent=self, model="cube", color=color.rgb32(60, 160, 40), scale=(0.3, 0.05, 0.15), position=(0.15, 0.6, 0))
        else:
            # lubenica: velika, zelena izvana, s prugama
            super().__init__(model="sphere", color=color.rgb32(40, 130, 40), scale=(1.2, 0.95, 0.95),
                             position=Vec3(polje[0], 0.15, polje[1]))
            for i in (-0.3, 0, 0.3):
                Entity(parent=self, model="sphere", color=color.rgb32(20, 80, 25), scale=(0.08, 1.01, 1.01), x=i)

    def update(self):
        self.rotation_y += 60 * time.dt
        self.y += math.sin(time.time() * 4) * 0.004


zmija = []
smjer = (0, 1)
novi_smjer = (0, 1)
hrana = []
bodovi = 0
kraj = False
napuhnuta_do = 0
odbrojavanje = 0

natpis = Text(text="", position=(-0.85, 0.47), scale=1.6, color=color.white)
poruka = Text(text="", origin=(0, 0), scale=2.5, color=color.yellow, y=0.1)


def slobodno_polje():
    zauzeto = {d.polje for d in zmija} | {h.polje for h in hrana}
    while True:
        p = (random.randrange(POLJE), random.randrange(POLJE))
        if p not in zauzeto:
            return p


def nova_hrana():
    # svaka cetvrta hrana (u prosjeku) je lubenica
    vrsta = "lubenica" if random.random() < 0.25 else "jabuka"
    hrana.append(Hrana(vrsta, slobodno_polje()))


def osvjezi_natpis():
    natpis.text = f"Bodovi: {bodovi}    Duzina: {len(zmija)}"


def nova_igra():
    global zmija, smjer, novi_smjer, hrana, bodovi, kraj, napuhnuta_do, odbrojavanje
    for d in zmija:
        destroy(d)
    for h in hrana:
        destroy(h)
    zmija = [Dio((POLJE // 2, 3 - i), glava=(i == 0)) for i in range(3)]
    for i, d in enumerate(zmija[1:]):
        d.color = ZELENA if i % 2 == 0 else ZELENA2
    smjer = novi_smjer = (0, 1)
    hrana = []
    nova_hrana()
    nova_hrana()
    bodovi = 0
    kraj = False
    napuhnuta_do = 0
    odbrojavanje = 0
    poruka.text = ""
    osvjezi_natpis()


def velicina_dijela(i):
    # rep je malo tanji od glave
    osnovna = 0.95 if i == 0 else max(0.55, 0.85 - i * 0.012)
    if time.time() < napuhnuta_do:
        # napuhnuta zmija je debela i lagano "dise"
        return osnovna * (1.9 + math.sin(time.time() * 10) * 0.12)
    return osnovna


def korak():
    global smjer, bodovi, kraj, napuhnuta_do
    smjer = novi_smjer
    glava = zmija[0].polje
    nova = (glava[0] + smjer[0], glava[1] + smjer[1])

    # udarac u ogradu ili u sebe
    if not (0 <= nova[0] < POLJE and 0 <= nova[1] < POLJE) or nova in [d.polje for d in zmija[:-1]]:
        kraj = True
        poruka.text = f"KRAJ!  Bodovi: {bodovi}\nPritisni R za novu igru"
        zmija[0].animate_color(color.red, duration=0.3)
        return

    pojedeno = next((h for h in hrana if h.polje == nova), None)

    # svaki dio ide na mjesto onog ispred sebe
    stari_rep = zmija[-1].polje
    for i in range(len(zmija) - 1, 0, -1):
        zmija[i].polje = zmija[i - 1].polje
    zmija[0].polje = nova

    if pojedeno:
        hrana.remove(pojedeno)
        destroy(pojedeno)
        if pojedeno.vrsta == "lubenica":
            bodovi += 5
            rast = 3
            napuhnuta_do = time.time() + NAPUHNUTA_TRAJE
            poruka.text = "NAPUHNUTA!"
            invoke(setattr, poruka, "text", "", delay=1.5)
        else:
            bodovi += 1
            rast = 1
        for _ in range(rast):
            d = Dio(stari_rep)
            d.color = ZELENA if len(zmija) % 2 == 1 else ZELENA2
            zmija.append(d)
        nova_hrana()
        osvjezi_natpis()


def update():
    global odbrojavanje
    if kraj:
        return
    odbrojavanje += time.dt
    if odbrojavanje >= KORAK:
        odbrojavanje -= KORAK
        korak()

    # glatko pomicanje i velicina svakog dijela
    for i, d in enumerate(zmija):
        cilj = Vec3(d.polje[0], 0.1, d.polje[1])
        d.position = lerp(d.position, cilj, min(1, time.dt * 14))
        v = velicina_dijela(i)
        d.scale = lerp(d.scale, Vec3(v, v, v), min(1, time.dt * 8))
    # glava gleda u smjeru kretanja
    zmija[0].look_at(zmija[0].position + Vec3(smjer[0], 0, smjer[1]))


def input(key):
    global novi_smjer
    tipke = {
        "up arrow": (0, 1), "w": (0, 1),
        "down arrow": (0, -1), "s": (0, -1),
        "left arrow": (-1, 0), "a": (-1, 0),
        "right arrow": (1, 0), "d": (1, 0),
    }
    if key in tipke:
        n = tipke[key]
        # ne moze se okrenuti ravno unazad
        if (n[0] + smjer[0], n[1] + smjer[1]) != (0, 0):
            novi_smjer = n
    if key == "r":
        nova_igra()
    if key == "escape":
        application.quit()


nova_igra()
app.run()
