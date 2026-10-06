"""Betmen - platformer u stilu Mario Bros (tkinter).

Kontrole:
  ← → / A D     hodanje
  Space / ↑     skok, u zraku još jednom = dupli skok,
                drži nakon duplog skoka = jedrenje plaštom
  X / J / F     pucanje
  1 2 3 / Q     promjena oružja (batarang, laser, bombe)
  Enter         nova igra nakon kraja

Skupljaj gljive (10 gljiva = +1 život), pucaj ili skači na zlikovce.
Jabuka te napravi 2x većim i pucaš 5 puta više. Velik razbijaš cigle glavom.
Laser probija više zlikovaca odjednom, bombe razbijaju i cigle.
"""
import math
import random
import tkinter as tk

T = 32                      # veličina pločice
VIEW_W, VIEW_H = 25 * T, 15 * T
FRAME_MS = 16
SOLID = "#B?XT"
SMALL = (22, 30)
INVULNERABLE = 90

# skakanje
GRAVITY = 0.6
JUMP_V = -12.5
DOUBLE_JUMP_V = -10.5
MOVE_V = 4
MAX_FALL = 12
GLIDE_FALL = 1.8
COYOTE = 6                  # još malo smiješ skočiti nakon ruba
JUMP_BUFFER = 8             # pritisak malo prije doskoka se pamti

# oružja
JUMP_KEYS = ("space", "up", "w")
SHOOT_KEYS = ("x", "j", "f")
WEAPON_NAMES = {"batarang": "BATARANG", "laser": "LASER", "bomba": "BOMBE"}
COOLDOWN = {"batarang": 14, "laser": 8, "bomba": 30}
WEAPON_COLOR = {"batarang": "#f5c518", "laser": "#ff3030", "bomba": "#111"}
BOMB_RADIUS = 80


def build_level():
    W, H = 130, 15
    g = [[" "] * W for _ in range(H)]

    def fill(x0, x1, y0, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = ch

    # tlo s rupama
    fill(0, W - 1, 13, 14, "#")
    for gap in (40, 70, 95):
        fill(gap, gap + 2, 13, 14, " ")

    # cijevi
    fill(24, 25, 11, 12, "T")
    fill(33, 34, 10, 12, "T")
    fill(56, 57, 11, 12, "T")

    # blokovi
    g[9][12] = "?"
    for x, ch in zip(range(15, 20), "B?B?B"):
        g[9][x] = ch
    g[5][17] = "?"
    fill(44, 50, 9, 9, "B")
    g[9][47] = "?"
    fill(74, 77, 10, 10, "B")
    fill(79, 84, 7, 7, "B")
    g[7][81] = "?"

    # novčići
    for x in range(27, 31):
        g[11][x] = "o"
    for x in (44, 46, 48, 50):
        g[8][x] = "o"
    for x in (60, 62, 64, 66):
        g[12][x] = "o"

    # gljive
    for x, y in ((8, 12), (10, 12), (45, 8), (47, 8), (49, 8), (61, 12),
                 (63, 12), (65, 12), (79, 6), (80, 6), (83, 6), (84, 6),
                 (90, 12), (105, 12), (115, 4)):
        g[y][x] = "M"

    # jabuke (moć) i oružja
    g[8][29] = "V"
    g[6][82] = "V"
    g[12][14] = "L"         # laser
    g[9][33] = "G"          # bombe

    # stepenice na kraju
    for i in range(8):
        fill(108 + i, 108 + i, 12 - i, 12, "#")

    # zastava
    fill(122, 122, 3, 12, "F")

    # zlikovci
    for x, y in ((20, 12), (30, 12), (38, 12), (48, 8), (52, 12), (62, 12),
                 (65, 12), (68, 12), (80, 12), (84, 12), (88, 12), (92, 12),
                 (100, 12), (103, 12), (106, 12)):
        g[y][x] = "E"

    g[12][3] = "P"
    return g


class Body:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.vx = self.vy = 0.0
        self.on_ground = False

    def overlaps(self, o):
        return (self.x < o.x + o.w and o.x < self.x + self.w
                and self.y < o.y + o.h and o.y < self.y + self.h)

    def center(self):
        return self.x + self.w / 2, self.y + self.h / 2


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Betmen")
        self.canvas = tk.Canvas(root, width=VIEW_W, height=VIEW_H,
                                bg="#2a3a6a", highlightthickness=0)
        self.canvas.pack()
        self.keys = set()
        root.bind("<KeyPress>", self.on_press)
        root.bind("<KeyRelease>", self.on_release)
        self.new_game()
        self.loop()

    # ---------- stanje igre ----------
    def new_game(self):
        self.lives = 3
        self.score = 0
        self.coins = 0
        self.mushrooms = 0
        self.weapons = ["batarang"]
        self.weapon = 0
        self.load_level()

    def load_level(self):
        self.grid = build_level()
        self.H, self.W = len(self.grid), len(self.grid[0])
        self.enemies = []
        self.bullets = []
        self.popups = []        # [x, y, timer] gljiva iskače iz bloka
        self.particles = []     # [x, y, vx, vy, life, boja, veličina]
        self.explosions = []    # [x, y, timer]
        for ty, row in enumerate(self.grid):
            for tx, ch in enumerate(row):
                if ch == "P":
                    self.player = Body(tx * T + 5, ty * T + 2, *SMALL)
                    row[tx] = " "
                elif ch == "E":
                    e = Body(tx * T + 2, ty * T + 2, 28, 30)
                    e.vx = -1
                    self.enemies.append(e)
                    row[tx] = " "
        self.big = False
        self.invulnerable = 0
        self.shoot_cd = 0
        self.coyote = 0
        self.jump_buffer = 0
        self.fresh_jump = False
        self.air_jumps = 1
        self.gliding = False
        self.facing = 1
        self.frame = 0
        self.cam_x = 0
        self.state = "play"     # play / dead / won / over
        self.timer = 0

    # ---------- ulaz ----------
    def on_press(self, ev):
        k = ev.keysym.lower()
        if k in JUMP_KEYS and k not in self.keys:
            self.jump_buffer = JUMP_BUFFER
            self.fresh_jump = True
        if k in ("1", "2", "3") and int(k) <= len(self.weapons):
            self.weapon = int(k) - 1
        elif k == "q" and k not in self.keys:
            self.weapon = (self.weapon + 1) % len(self.weapons)
        self.keys.add(k)
        if k == "return" and self.state in ("won", "over"):
            self.new_game()

    def on_release(self, ev):
        k = ev.keysym.lower()
        self.keys.discard(k)
        # kratki pritisak = niži skok
        if k in JUMP_KEYS and self.player.vy < -4:
            self.player.vy = -4

    def holding(self, keys):
        return any(k in self.keys for k in keys)

    # ---------- fizika ----------
    def solid(self, tx, ty):
        if tx < 0 or tx >= self.W:
            return True
        if ty < 0 or ty >= self.H:
            return False
        return self.grid[ty][tx] in SOLID

    def tiles_of(self, b):
        for ty in range(int(b.y // T), int((b.y + b.h - 1) // T) + 1):
            for tx in range(int(b.x // T), int((b.x + b.w - 1) // T) + 1):
                yield tx, ty

    def hits_solid(self, b):
        return any(self.solid(tx, ty) for tx, ty in self.tiles_of(b))

    def move(self, b, gravity=GRAVITY, max_fall=MAX_FALL):
        """Pomakne tijelo; vraća (udario_zid, pločica_udarena_glavom)."""
        hit_wall = False
        b.x += b.vx
        for tx, ty in self.tiles_of(b):
            if self.solid(tx, ty):
                b.x = tx * T - b.w if b.vx > 0 else (tx + 1) * T
                hit_wall = True
                break

        bumped = None
        b.vy = min(b.vy + gravity, max_fall)
        b.y += b.vy
        b.on_ground = False
        for tx, ty in self.tiles_of(b):
            if self.solid(tx, ty):
                if b.vy > 0:
                    b.y = ty * T - b.h
                    b.on_ground = True
                else:
                    b.y = (ty + 1) * T
                    bumped = (tx, ty)
                b.vy = 0
                break
        return hit_wall, bumped

    # ---------- efekti ----------
    def burst(self, x, y, color, n=8, speed=3.0, size=4, up=0.0):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.5, 1) * speed
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v - up,
                                   random.randint(15, 30), color, size])

    def dust(self, x, y):
        for d in (-1, 1):
            for _ in range(4):
                self.particles.append([x, y, d * random.uniform(0.5, 2.5),
                                       random.uniform(-1.2, -0.2),
                                       random.randint(12, 20), "#c8c8d8", 4])

    def break_brick(self, tx, ty):
        self.grid[ty][tx] = " "
        self.score += 50
        self.burst(tx * T + T / 2, ty * T + T / 2, "#8a4a3a", n=10,
                   speed=4, size=6, up=3)

    # ---------- moći i oružja ----------
    def grow(self):
        if self.big:
            return
        p = self.player
        self.big = True
        p.x -= SMALL[0] / 2
        p.y -= SMALL[1]
        p.w, p.h = SMALL[0] * 2, SMALL[1] * 2
        # ako je narastao u zid ili strop, pogurni ga
        for _ in range(SMALL[1]):
            if not self.hits_solid(p):
                break
            p.y += 1
        self.burst(*p.center(), "#fff59d", n=20, speed=5)

    def shrink(self):
        p = self.player
        self.big = False
        p.x += SMALL[0] / 2
        p.y += SMALL[1]
        p.w, p.h = SMALL
        self.invulnerable = INVULNERABLE

    def get_hit(self):
        if self.invulnerable:
            return
        if self.big:
            self.shrink()
        else:
            self.die()

    def pick_weapon(self, kind):
        if kind not in self.weapons:
            self.weapons.append(kind)
        self.weapon = self.weapons.index(kind)
        self.score += 500
        self.burst(*self.player.center(), WEAPON_COLOR[kind], n=16, speed=4)

    def shoot(self):
        p = self.player
        kind = self.weapons[self.weapon]
        f = self.facing
        x = p.x + p.w if f > 0 else p.x - 14
        y = p.y + p.h * 0.4
        spreads = (-2, -1, 0, 1, 2) if self.big else (0,)
        for s in spreads:
            if kind == "batarang":
                b = Body(x, y, 14, 8)
                b.vx, b.vy, b.life = 9 * f, s, 50
            elif kind == "laser":
                b = Body(x, y, 24, 4)
                b.vx, b.vy, b.life = 14 * f, s * 0.8, 40
            else:
                b = Body(x, y - 6, 10, 10)
                b.vx, b.vy, b.life = (5 + s) * f, -6 + s * 0.6, 90
            b.kind = kind
            self.bullets.append(b)
        self.shoot_cd = COOLDOWN[kind]

    def kill_enemy(self, e, points=200):
        self.enemies.remove(e)
        self.score += points
        self.burst(*e.center(), "#7a2a9a", n=10, speed=3)

    def explode(self, b):
        cx, cy = b.center()
        self.explosions.append([cx, cy, 18])
        self.burst(cx, cy, "#ff9a20", n=18, speed=5)
        for e in self.enemies[:]:
            ex, ey = e.center()
            if math.hypot(ex - cx, ey - cy) < BOMB_RADIUS:
                self.kill_enemy(e)
        for ty in range(int((cy - BOMB_RADIUS) // T), int((cy + BOMB_RADIUS) // T) + 1):
            for tx in range(int((cx - BOMB_RADIUS) // T), int((cx + BOMB_RADIUS) // T) + 1):
                if (0 <= tx < self.W and 0 <= ty < self.H and self.grid[ty][tx] == "B"
                        and math.hypot(tx * T + T / 2 - cx, ty * T + T / 2 - cy) < BOMB_RADIUS):
                    self.break_brick(tx, ty)

    def collect_mushroom(self):
        self.mushrooms += 1
        self.score += 500
        if self.mushrooms % 10 == 0:
            self.lives += 1

    # ---------- glavna petlja ----------
    def update(self):
        self.frame += 1
        self.update_effects()
        if self.state == "dead":
            self.timer -= 1
            if self.timer <= 0:
                if self.lives > 0:
                    self.load_level()
                else:
                    self.state = "over"
            return
        if self.state != "play":
            return

        p = self.player
        if self.invulnerable:
            self.invulnerable -= 1
        if self.shoot_cd:
            self.shoot_cd -= 1

        left = "left" in self.keys or "a" in self.keys
        right = "right" in self.keys or "d" in self.keys
        p.vx = (right - left) * MOVE_V
        if p.vx:
            self.facing = 1 if p.vx > 0 else -1

        self.update_jump(p)

        if self.holding(SHOOT_KEYS) and not self.shoot_cd:
            self.shoot()

        self.update_items(p)
        self.update_bullets()
        if not self.update_enemies(p):
            return

        if p.y > self.H * T:
            self.die()

        target = p.x - VIEW_W / 3
        self.cam_x = max(0, min(target, self.W * T - VIEW_W))

    def update_jump(self, p):
        holding_jump = self.holding(JUMP_KEYS)
        if p.on_ground:
            self.coyote = COYOTE
            self.air_jumps = 1
        elif self.coyote:
            self.coyote -= 1

        if self.jump_buffer:
            if self.coyote:
                p.vy = JUMP_V
                self.coyote = 0
                self.jump_buffer = 0
                self.dust(p.x + p.w / 2, p.y + p.h)
            elif self.fresh_jump and self.air_jumps:
                p.vy = DOUBLE_JUMP_V
                self.air_jumps -= 1
                self.jump_buffer = 0
                self.burst(p.x + p.w / 2, p.y + p.h, "#9aa0c8", n=10, speed=2.5)
            else:
                self.jump_buffer -= 1
        self.fresh_jump = False

        # na vrhu skoka malo lebdi, nakon duplog skoka može jedriti
        gravity = GRAVITY * 0.55 if holding_jump and abs(p.vy) < 2.5 else GRAVITY
        self.gliding = (holding_jump and not self.air_jumps
                        and p.vy >= 0 and not p.on_ground)
        max_fall = GLIDE_FALL if self.gliding else MAX_FALL

        was_ground, fall_speed = p.on_ground, p.vy
        _, bumped = self.move(p, gravity, max_fall)
        if p.on_ground and not was_ground and fall_speed > 5:
            self.dust(p.x + p.w / 2, p.y + p.h)

        if bumped:
            tx, ty = bumped
            ch = self.grid[ty][tx]
            if ch == "?":
                self.grid[ty][tx] = "X"
                self.collect_mushroom()
                self.popups.append([tx * T + 4, ty * T - 20, 24])
            elif ch == "B" and self.big:
                self.break_brick(tx, ty)

    def update_items(self, p):
        for tx, ty in self.tiles_of(p):
            if not (0 <= ty < self.H and 0 <= tx < self.W):
                continue
            ch = self.grid[ty][tx]
            if ch in "oMVLG":
                self.grid[ty][tx] = " "
            if ch == "o":
                self.coins += 1
                self.score += 100
            elif ch == "M":
                self.collect_mushroom()
            elif ch == "V":
                self.score += 1000
                self.grow()
            elif ch == "L":
                self.pick_weapon("laser")
            elif ch == "G":
                self.pick_weapon("bomba")
            elif ch == "F" and self.state == "play":
                self.state = "won"
                self.score += 1000

    def update_bullets(self):
        for b in self.bullets[:]:
            if b.kind == "bomba":
                b.vy += 0.4
            b.x += b.vx
            b.y += b.vy
            b.life -= 1
            if b.kind == "bomba":
                if (b.life <= 0 or self.hits_solid(b)
                        or any(b.overlaps(e) for e in self.enemies)):
                    self.bullets.remove(b)
                    self.explode(b)
                continue
            if b.life <= 0 or self.hits_solid(b):
                self.bullets.remove(b)
                continue
            for e in self.enemies[:]:
                if b.overlaps(e):
                    self.kill_enemy(e)
                    if b.kind == "batarang":     # laser probija dalje
                        self.bullets.remove(b)
                        break

    def update_enemies(self, p):
        """Vraća False ako je igrač upravo poginuo."""
        for e in self.enemies[:]:
            if abs(e.x - p.x) > VIEW_W:       # miruju dok su daleko
                continue
            hit_wall, _ = self.move(e)
            if hit_wall:
                e.vx = -e.vx
            if e.y > self.H * T:
                self.enemies.remove(e)
                continue
            if p.overlaps(e):
                if p.vy > 0 and p.y + p.h - e.y < 14:
                    self.kill_enemy(e, 100)
                    p.vy = -8
                    self.air_jumps = 1
                else:
                    self.get_hit()
                    if self.state != "play":
                        return False
        return True

    def update_effects(self):
        for pt in self.particles[:]:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[3] += 0.2
            pt[4] -= 1
            if pt[4] <= 0:
                self.particles.remove(pt)
        for ex in self.explosions[:]:
            ex[2] -= 1
            if ex[2] <= 0:
                self.explosions.remove(ex)
        for pop in self.popups[:]:
            pop[1] -= 1.5
            pop[2] -= 1
            if pop[2] <= 0:
                self.popups.remove(pop)

    def die(self):
        self.lives -= 1
        self.state = "dead"
        self.timer = 60

    # ---------- crtanje ----------
    def draw(self):
        c = self.canvas
        c.delete("all")
        cx = self.cam_x

        # noćni Gotham: mjesec i zgrade (paralaksa)
        c.create_oval(VIEW_W - 160, 30, VIEW_W - 80, 110, fill="#f5f0c8", outline="")
        for i in range(30):
            x = i * 110 - cx * 0.3
            h = 120 + (i * 53) % 140
            c.create_rectangle(x, VIEW_H - 64 - h, x + 90, VIEW_H, fill="#1b2545", outline="")
            for wy in range(VIEW_H - 50 - h, VIEW_H - 80, 28):
                for wx in (12, 40, 68):
                    if (i * 7 + wx + wy) % 3:
                        c.create_rectangle(x + wx, wy, x + wx + 10, wy + 12,
                                           fill="#e8c860", outline="")

        first, last = int(cx // T), int((cx + VIEW_W) // T) + 1
        for ty in range(self.H):
            for tx in range(max(0, first), min(self.W, last + 1)):
                ch = self.grid[ty][tx]
                if ch != " ":
                    top = ty == 0 or self.grid[ty - 1][tx] != ch
                    self.draw_tile(ch, tx * T - cx, ty * T, top)

        for x, y, _ in self.popups:
            self.draw_mushroom(x - cx, y)

        for e in self.enemies:
            self.draw_enemy(e.x - cx, e.y)

        for b in self.bullets:
            self.draw_bullet(b, b.x - cx, b.y)

        blink = self.invulnerable and self.frame % 8 < 4
        dying = self.state == "dead" and self.timer % 8 < 4
        if not (blink or dying):
            self.draw_batman(self.player.x - cx, self.player.y)

        for x, y, t in self.explosions:
            r = (18 - t) * 5 + 10
            c.create_oval(x - cx - r, y - r, x - cx + r, y + r,
                          fill="#ff9a20" if t > 9 else "", outline="#fff59d", width=3)
            if t > 9:
                c.create_oval(x - cx - r / 2, y - r / 2, x - cx + r / 2, y + r / 2,
                              fill="#fff59d", outline="")

        for x, y, _, _, life, col, size in self.particles:
            s = size * min(1, life / 10)
            c.create_rectangle(x - cx - s / 2, y - s / 2, x - cx + s / 2, y + s / 2,
                               fill=col, outline="")

        hud = (f"BODOVI {self.score:06d}   NOVČIĆI {self.coins:02d}   "
               f"GLJIVE {self.mushrooms:02d}   ŽIVOTI {self.lives}")
        c.create_text(12, 10, anchor="nw", fill="white",
                      font=("Consolas", 13, "bold"), text=hud)
        self.draw_weapon_bar()

        msg = {"won": "GOTHAM JE SPAŠEN!\nEnter za novu igru",
               "over": "KRAJ IGRE\nEnter za novu igru"}.get(self.state)
        if msg:
            c.create_rectangle(VIEW_W / 2 - 220, VIEW_H / 2 - 60,
                               VIEW_W / 2 + 220, VIEW_H / 2 + 60,
                               fill="#000", outline="#f5c518", width=3)
            c.create_text(VIEW_W / 2, VIEW_H / 2, fill="#f5c518",
                          font=("Consolas", 20, "bold"), text=msg,
                          justify="center")

    def draw_weapon_bar(self):
        c = self.canvas
        x = 12
        for i, kind in enumerate(self.weapons):
            selected = i == self.weapon
            label = f"{i + 1} {WEAPON_NAMES[kind]}"
            w = 12 + len(label) * 9
            c.create_rectangle(x, 34, x + w, 56,
                               fill="#f5c518" if selected else "#1a1a28",
                               outline="#f5c518", width=2)
            c.create_text(x + w / 2, 45, text=label,
                          fill="#111" if selected else "#f5c518",
                          font=("Consolas", 11, "bold"))
            x += w + 6
        if self.big:
            c.create_text(x + 8, 45, anchor="w", text="MOĆ x5!", fill="#ff6060",
                          font=("Consolas", 13, "bold"))

    def draw_tile(self, ch, x, y, top):
        c = self.canvas
        if ch == "#":
            c.create_rectangle(x, y, x + T, y + T, fill="#4a4a58", outline="#2a2a34")
            c.create_line(x, y + T / 2, x + T, y + T / 2, fill="#2a2a34")
        elif ch == "B":
            c.create_rectangle(x, y, x + T, y + T, fill="#8a4a3a", outline="#3a1a10")
            c.create_line(x, y + T / 2, x + T, y + T / 2, fill="#3a1a10")
            c.create_line(x + T / 2, y, x + T / 2, y + T / 2, fill="#3a1a10")
        elif ch == "?":
            pulse = "#ffd34d" if (self.frame // 20) % 2 else "#f5b800"
            c.create_rectangle(x, y, x + T, y + T, fill=pulse, outline="#8a5a00", width=2)
            c.create_text(x + T / 2, y + T / 2, text="?", fill="#8a3a00",
                          font=("Consolas", 16, "bold"))
        elif ch == "X":
            c.create_rectangle(x, y, x + T, y + T, fill="#6a4a2a", outline="#3a2a0a", width=2)
        elif ch == "T":
            c.create_rectangle(x, y, x + T, y + T, fill="#2fa52f", outline="#0d5e0d", width=2)
        elif ch == "o":
            c.create_oval(x + 9, y + 5, x + T - 9, y + T - 5, fill="#ffd700",
                          outline="#b8860b", width=2)
        elif ch == "M":
            self.draw_mushroom(x + 4, y + 4)
        elif ch == "V":
            self.draw_apple(x, y)
        elif ch in "LG":
            self.draw_weapon_pickup(ch, x, y)
        elif ch == "F":
            c.create_rectangle(x + 14, y, x + 18, y + T, fill="#ddd", outline="")
            if top:
                c.create_oval(x + 10, y - 10, x + 22, y + 2, fill="#f5c518", outline="")
                c.create_polygon(x + 14, y + 4, x - 24, y + 4, x - 24, y + 28,
                                 x + 14, y + 28, fill="#111", outline="#f5c518")
                self.draw_bat_symbol(x - 5, y + 16, 1.0)

    def draw_glow(self, x, y):
        glow = 3 if (self.frame // 10) % 2 else 0
        self.canvas.create_oval(x + 2 - glow, y + 4 - glow, x + 30 + glow,
                                y + 32 + glow, fill="", outline="#fff59d", width=2)

    def draw_weapon_pickup(self, ch, x, y):
        c = self.canvas
        bob = 2 * math.sin(self.frame / 8)
        y += bob
        self.draw_glow(x, y)
        if ch == "L":
            c.create_rectangle(x + 6, y + 13, x + 26, y + 19, fill="#8a8aa0", outline="#333")
            c.create_rectangle(x + 8, y + 18, x + 13, y + 26, fill="#555", outline="")
            c.create_oval(x + 23, y + 12, x + 29, y + 20, fill="#ff3030", outline="")
        else:
            c.create_oval(x + 7, y + 10, x + 25, y + 28, fill="#111", outline="#555")
            c.create_line(x + 20, y + 12, x + 24, y + 5, fill="#c8a060", width=2)
            spark = "#fff59d" if self.frame % 6 < 3 else "#ff9a20"
            c.create_oval(x + 22, y + 2, x + 27, y + 7, fill=spark, outline="")

    def draw_mushroom(self, x, y):
        c = self.canvas
        c.create_rectangle(x + 8, y + 12, x + 16, y + 24, fill="#f5e6c8", outline="")
        c.create_arc(x, y, x + 24, y + 26, start=0, extent=180, fill="#e52521", outline="")
        for dx, dy in ((5, 4), (14, 2), (17, 8)):
            c.create_oval(x + dx, y + dy, x + dx + 5, y + dy + 5, fill="white", outline="")

    def draw_apple(self, x, y):
        c = self.canvas
        self.draw_glow(x, y)
        c.create_oval(x + 5, y + 8, x + 27, y + 30, fill="#e52521", outline="#8a0000")
        c.create_line(x + 16, y + 9, x + 17, y + 2, fill="#5a3000", width=2)
        c.create_oval(x + 17, y + 1, x + 26, y + 7, fill="#2fb52f", outline="")
        c.create_oval(x + 9, y + 12, x + 14, y + 17, fill="#ff9a9a", outline="")

    def draw_bat_symbol(self, cx, cy, s):
        self.canvas.create_polygon(
            cx - 9 * s, cy, cx - 6 * s, cy - 3 * s, cx - 2 * s, cy - 2 * s,
            cx - 1 * s, cy - 4 * s, cx, cy - 2 * s, cx + 1 * s, cy - 4 * s,
            cx + 2 * s, cy - 2 * s, cx + 6 * s, cy - 3 * s, cx + 9 * s, cy,
            cx + 4 * s, cy + 1 * s, cx, cy + 4 * s, cx - 4 * s, cy + 1 * s,
            fill="#f5c518", outline="")

    def draw_batman(self, X, Y):
        c = self.canvas
        p = self.player
        s = 2 if self.big else 1
        f = self.facing

        def px(x):
            return X + s * (x if f > 0 else SMALL[0] - x)

        def rect(x0, y0, x1, y1, col):
            a, b = sorted((px(x0), px(x1)))
            c.create_rectangle(a, Y + s * y0, b, Y + s * y1, fill=col, outline="")

        def poly(pts, col):
            flat = []
            for x, y in pts:
                flat += [px(x), Y + s * y]
            c.create_polygon(*flat, fill=col, outline="")

        moving = p.vx and p.on_ground
        step = 3 if moving and (self.frame // 6) % 2 else 0
        if not p.on_ground:
            step = 4

        # plašt: raširen kao krila dok jedri, inače vijori
        if self.gliding:
            flap = 2 * math.sin(self.frame / 3)
            poly([(6, 10), (16, 10), (34, 14 + flap), (26, 20), (20, 17),
                  (11, 22), (2, 17), (-4, 20), (-12, 14 + flap)], "#1a1a28")
        else:
            flap = -4 if (p.vx or not p.on_ground) else 0
            poly([(6, 10), (16, 10), (14, 26), (2 + flap, 30), (0 + flap, 20)], "#1a1a28")

        # noge
        rect(5 - step, 23, 10 - step, 30, "#55556a")
        rect(12 + step, 23, 17 + step, 30, "#55556a")
        rect(4 - step, 27, 10 - step, 30, "#111")
        rect(12 + step, 27, 18 + step, 30, "#111")

        # tijelo
        rect(4, 11, 18, 24, "#6b6b80")
        rect(4, 20, 18, 23, "#f5c518")             # pojas
        sx = px(11)
        c.create_oval(sx - 5 * s, Y + 13 * s, sx + 5 * s, Y + 18 * s,
                      fill="#f5c518", outline="")
        c.create_rectangle(sx - 3 * s, Y + 15 * s, sx + 3 * s, Y + 16 * s,
                           fill="#111", outline="")

        # ruka s oružjem
        kind = self.weapons[self.weapon]
        if self.shoot_cd > COOLDOWN[kind] - 6:
            rect(16, 13, 23, 16, "#6b6b80")
            rect(22, 12, 26, 17, WEAPON_COLOR[kind])
        else:
            rect(15, 13, 18, 20, "#6b6b80")
            rect(15, 19, 19, 22, WEAPON_COLOR[kind])

        # glava (maska s ušima)
        rect(6, 2, 17, 11, "#1a1a28")
        poly([(6, 2), (7, -3), (9, 2)], "#1a1a28")
        poly([(14, 2), (16, -3), (17, 2)], "#1a1a28")
        rect(11, 7, 17, 11, "#ffc890")              # brada
        rect(12, 9, 16, 10, "#8a4a3a")              # usta
        rect(12, 5, 16, 6, "white")                 # oko

    def draw_enemy(self, x, y):
        """Zlikovac: ljubičasti klaun sa zelenom kosom."""
        c = self.canvas
        wob = 2 if (self.frame // 10) % 2 else -2
        c.create_oval(x + 2 + wob, y + 24, x + 12 + wob, y + 30, fill="#2a0a3a", outline="")
        c.create_oval(x + 16 - wob, y + 24, x + 26 - wob, y + 30, fill="#2a0a3a", outline="")
        c.create_rectangle(x + 5, y + 14, x + 23, y + 26, fill="#7a2a9a", outline="")
        c.create_oval(x + 5, y + 2, x + 23, y + 18, fill="#f0f0f0", outline="")
        for hx in (3, 8, 14, 19):
            c.create_oval(x + hx, y - 2, x + hx + 7, y + 7, fill="#3fbf3f", outline="")
        c.create_line(x + 8, y + 6, x + 12, y + 8, fill="black", width=2)
        c.create_line(x + 20, y + 6, x + 16, y + 8, fill="black", width=2)
        c.create_oval(x + 9, y + 8, x + 12, y + 11, fill="black", outline="")
        c.create_oval(x + 16, y + 8, x + 19, y + 11, fill="black", outline="")
        c.create_arc(x + 8, y + 9, x + 20, y + 16, start=180, extent=180,
                     style="arc", outline="#d01010", width=2)

    def draw_bullet(self, b, x, y):
        c = self.canvas
        if b.kind == "batarang":
            cx, cy = x + 7, y + 4
            if (self.frame // 3) % 2:
                self.draw_bat_symbol(cx, cy, 0.8)
            else:
                c.create_polygon(cx, cy - 6, cx + 3, cy, cx, cy + 6, cx - 3, cy,
                                 fill="#f5c518", outline="")
        elif b.kind == "laser":
            tail = -b.vx * 1.5
            c.create_line(x + 12 + tail, y + 2, x + 24, y + 2, fill="#ff3030", width=5)
            c.create_line(x + 12 + tail / 2, y + 2, x + 24, y + 2, fill="#ffd0d0", width=2)
        else:
            c.create_oval(x, y, x + 10, y + 10, fill="#111", outline="#666")
            spark = "#fff59d" if self.frame % 4 < 2 else "#ff9a20"
            c.create_oval(x + 6, y - 3, x + 10, y + 1, fill=spark, outline="")

    def loop(self):
        self.update()
        self.draw()
        self.root.after(FRAME_MS, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    Game(root)
    root.mainloop()
