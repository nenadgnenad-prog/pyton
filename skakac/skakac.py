
"""Skakač - mali platformer u stilu Mario Bros (tkinter).

Strelice / A,D za kretanje, Space ili strelica gore za skok.
Skoči neprijatelju na glavu, udari ? blok odozdo, dođi do zastave.
Enter za novu igru nakon kraja.
"""
import tkinter as tk

T = 32                      # veličina pločice
VIEW_W, VIEW_H = 25 * T, 15 * T
GRAVITY = 0.6
JUMP_V = -12
MOVE_V = 4
MAX_FALL = 12
FRAME_MS = 16
SOLID = "#B?XT"


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
    for x in range(44, 51):
        g[8][x] = "o"
    for x in range(60, 67):
        g[12][x] = "o"
    for x in range(79, 85):
        g[6][x] = "o"

    # stepenice na kraju
    for i in range(8):
        fill(108 + i, 108 + i, 12 - i, 12, "#")

    # zastava
    fill(122, 122, 3, 12, "F")

    # neprijatelji
    for x, y in ((20, 12), (38, 12), (48, 8), (62, 12), (65, 12),
                 (80, 12), (88, 12), (100, 12), (103, 12)):
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


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Skakač")
        self.canvas = tk.Canvas(root, width=VIEW_W, height=VIEW_H,
                                bg="#5c94fc", highlightthickness=0)
        self.canvas.pack()
        self.keys = set()
        self.jump_pressed = False
        root.bind("<KeyPress>", self.on_press)
        root.bind("<KeyRelease>", self.on_release)
        self.new_game()
        self.loop()

    # ---------- stanje igre ----------
    def new_game(self):
        self.lives = 3
        self.score = 0
        self.coins = 0
        self.load_level()

    def load_level(self):
        self.grid = build_level()
        self.H, self.W = len(self.grid), len(self.grid[0])
        self.enemies = []
        self.popups = []        # (x, y, timer) animacija novčića iz bloka
        for ty, row in enumerate(self.grid):
            for tx, ch in enumerate(row):
                if ch == "P":
                    self.player = Body(tx * T + 5, ty * T + 2, 22, 30)
                    row[tx] = " "
                elif ch == "E":
                    e = Body(tx * T + 2, ty * T + 4, 28, 28)
                    e.vx = -1
                    self.enemies.append(e)
                    row[tx] = " "
        self.facing = 1
        self.frame = 0
        self.cam_x = 0
        self.state = "play"     # play / dead / won / over
        self.timer = 0

    # ---------- ulaz ----------
    def on_press(self, ev):
        k = ev.keysym.lower()
        if k in ("space", "up", "w") and k not in self.keys:
            self.jump_pressed = True
        self.keys.add(k)
        if k == "return" and self.state in ("won", "over"):
            self.new_game()

    def on_release(self, ev):
        k = ev.keysym.lower()
        self.keys.discard(k)
        # kratki pritisak = niži skok
        if k in ("space", "up", "w") and self.player.vy < -4:
            self.player.vy = -4

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

    def move(self, b):
        """Pomakne tijelo; vraća (udario_zid, pločica_udarena_glavom)."""
        hit_wall = False
        b.x += b.vx
        for tx, ty in self.tiles_of(b):
            if self.solid(tx, ty):
                b.x = tx * T - b.w if b.vx > 0 else (tx + 1) * T
                hit_wall = True
                break

        bumped = None
        b.vy = min(b.vy + GRAVITY, MAX_FALL)
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

    def update(self):
        self.frame += 1
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
        left = "left" in self.keys or "a" in self.keys
        right = "right" in self.keys or "d" in self.keys
        p.vx = (right - left) * MOVE_V
        if p.vx:
            self.facing = 1 if p.vx > 0 else -1
        if self.jump_pressed and p.on_ground:
            p.vy = JUMP_V
        self.jump_pressed = False

        _, bumped = self.move(p)
        if bumped and self.grid[bumped[1]][bumped[0]] == "?":
            tx, ty = bumped
            self.grid[ty][tx] = "X"
            self.coins += 1
            self.score += 200
            self.popups.append([tx * T + 8, ty * T - 16, 20])

        # skupljanje novčića i zastava
        for tx, ty in self.tiles_of(p):
            if 0 <= ty < self.H and 0 <= tx < self.W:
                ch = self.grid[ty][tx]
                if ch == "o":
                    self.grid[ty][tx] = " "
                    self.coins += 1
                    self.score += 100
                elif ch == "F":
                    self.state = "won"
                    self.score += 1000

        # neprijatelji
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
                    self.enemies.remove(e)
                    p.vy = -8
                    self.score += 100
                else:
                    self.die()
                    return

        for pop in self.popups[:]:
            pop[1] -= 2
            pop[2] -= 1
            if pop[2] <= 0:
                self.popups.remove(pop)

        if p.y > self.H * T:
            self.die()

        target = p.x - VIEW_W / 3
        self.cam_x = max(0, min(target, self.W * T - VIEW_W))

    def die(self):
        self.lives -= 1
        self.state = "dead"
        self.timer = 60

    # ---------- crtanje ----------
    def draw(self):
        c = self.canvas
        c.delete("all")
        cx = self.cam_x

        # oblaci (paralaksa)
        for i in range(12):
            x = (i * 340 + 80) - cx * 0.4
            y = 50 + (i * 37) % 90
            c.create_oval(x, y, x + 90, y + 34, fill="white", outline="")
            c.create_oval(x + 25, y - 16, x + 70, y + 20, fill="white", outline="")

        first, last = int(cx // T), int((cx + VIEW_W) // T) + 1
        for ty in range(self.H):
            for tx in range(max(0, first), min(self.W, last + 1)):
                ch = self.grid[ty][tx]
                if ch != " ":
                    top = ty == 0 or self.grid[ty - 1][tx] != ch
                    self.draw_tile(ch, tx * T - cx, ty * T, top)

        for x, y, _ in self.popups:
            c.create_oval(x - cx, y, x - cx + 16, y + 20, fill="#ffd700",
                          outline="#b8860b", width=2)

        for e in self.enemies:
            self.draw_enemy(e.x - cx, e.y)

        if self.state != "dead" or self.timer % 8 < 4:
            self.draw_player(self.player.x - cx, self.player.y)

        c.create_text(12, 10, anchor="nw", fill="white",
                      font=("Consolas", 14, "bold"),
                      text=f"BODOVI {self.score:06d}   NOVČIĆI {self.coins:02d}"
                           f"   ŽIVOTI {self.lives}")

        msg = {"won": "POBJEDA! 🎉\nEnter za novu igru",
               "over": "KRAJ IGRE\nEnter za novu igru"}.get(self.state)
        if msg:
            c.create_rectangle(VIEW_W / 2 - 200, VIEW_H / 2 - 60,
                               VIEW_W / 2 + 200, VIEW_H / 2 + 60,
                               fill="#000", outline="white", width=3)
            c.create_text(VIEW_W / 2, VIEW_H / 2, fill="white",
                          font=("Consolas", 20, "bold"), text=msg,
                          justify="center")

    def draw_tile(self, ch, x, y, top):
        c = self.canvas
        if ch == "#":
            c.create_rectangle(x, y, x + T, y + T, fill="#c84c0c", outline="#7a2e06")
            c.create_line(x, y + T / 2, x + T, y + T / 2, fill="#7a2e06")
        elif ch == "B":
            c.create_rectangle(x, y, x + T, y + T, fill="#e0702a", outline="#5a2000")
            c.create_line(x, y + T / 2, x + T, y + T / 2, fill="#5a2000")
            c.create_line(x + T / 2, y, x + T / 2, y + T / 2, fill="#5a2000")
        elif ch == "?":
            pulse = "#ffd34d" if (self.frame // 20) % 2 else "#f5b800"
            c.create_rectangle(x, y, x + T, y + T, fill=pulse, outline="#8a5a00", width=2)
            c.create_text(x + T / 2, y + T / 2, text="?", fill="#8a3a00",
                          font=("Consolas", 16, "bold"))
        elif ch == "X":
            c.create_rectangle(x, y, x + T, y + T, fill="#8a5a2a", outline="#4a2a0a", width=2)
        elif ch == "T":
            c.create_rectangle(x, y, x + T, y + T, fill="#2fb52f", outline="#0d5e0d", width=2)
        elif ch == "o":
            c.create_oval(x + 9, y + 5, x + T - 9, y + T - 5, fill="#ffd700",
                          outline="#b8860b", width=2)
        elif ch == "F":
            c.create_rectangle(x + 14, y, x + 18, y + T, fill="#ddd", outline="")
            if top:
                c.create_oval(x + 10, y - 10, x + 22, y + 2, fill="#2fb52f", outline="")
                c.create_polygon(x + 14, y + 4, x - 20, y + 16, x + 14, y + 28,
                                 fill="#2fb52f", outline="#0d5e0d")

    def draw_player(self, x, y):
        c = self.canvas
        w, f = 22, self.facing
        p = self.player
        # noge (animacija hoda)
        step = 3 if p.vx and p.on_ground and (self.frame // 6) % 2 else 0
        if not p.on_ground:
            step = 4
        c.create_rectangle(x + 2 - step, y + 25, x + 10 - step, y + 30, fill="#5a3000", outline="")
        c.create_rectangle(x + 12 + step, y + 25, x + 20 + step, y + 30, fill="#5a3000", outline="")
        # tijelo
        c.create_rectangle(x + 2, y + 13, x + w - 2, y + 21, fill="#e52521", outline="")
        c.create_rectangle(x + 5, y + 17, x + w - 5, y + 26, fill="#1c3fd6", outline="")
        c.create_oval(x + 7, y + 18, x + 9, y + 20, fill="#ffd700", outline="")
        c.create_oval(x + 13, y + 18, x + 15, y + 20, fill="#ffd700", outline="")
        # glava
        c.create_oval(x + 3, y + 3, x + w - 3, y + 15, fill="#ffc890", outline="")
        c.create_rectangle(x + 2, y, x + w - 2, y + 5, fill="#e52521", outline="")
        brim = (x + w - 2, x + w + 4) if f > 0 else (x - 4, x + 2)
        c.create_rectangle(brim[0], y + 3, brim[1], y + 6, fill="#e52521", outline="")
        ex = x + 14 if f > 0 else x + 6
        c.create_oval(ex, y + 7, ex + 3, y + 10, fill="black", outline="")
        mx = x + 11 if f > 0 else x + 5
        c.create_rectangle(mx, y + 11, mx + 7, y + 13, fill="#4a2000", outline="")

    def draw_enemy(self, x, y):
        c = self.canvas
        wob = 2 if (self.frame // 10) % 2 else -2
        c.create_oval(x + 2 + wob, y + 22, x + 12 + wob, y + 28, fill="#222", outline="")
        c.create_oval(x + 16 - wob, y + 22, x + 26 - wob, y + 28, fill="#222", outline="")
        c.create_rectangle(x + 7, y + 14, x + 21, y + 24, fill="#f0d0a0", outline="")
        c.create_arc(x, y, x + 28, y + 30, start=0, extent=180, fill="#a0522d", outline="")
        c.create_oval(x + 7, y + 7, x + 12, y + 14, fill="white", outline="")
        c.create_oval(x + 16, y + 7, x + 21, y + 14, fill="white", outline="")
        c.create_oval(x + 9, y + 9, x + 11, y + 13, fill="black", outline="")
        c.create_oval(x + 17, y + 9, x + 19, y + 13, fill="black", outline="")

    def loop(self):
        self.update()
        self.draw()
        self.root.after(FRAME_MS, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    Game(root)
    root.mainloop()
