"""Zmija - jednostavna igra u tkinteru.

Strelice za kretanje, Space za novu igru.
"""
import random
import tkinter as tk

CELL = 24
COLS, ROWS = 25, 20
SPEED_MS = 110


class Zmija:
    def __init__(self, root):
        self.root = root
        root.title("Zmija")
        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg="#1e1e2e", highlightthickness=0)
        self.canvas.pack()
        root.bind("<Key>", self.on_key)
        self.best = 0
        self.reset()
        self.tick()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_dir = (1, 0)
        self.score = 0
        self.alive = True
        self.place_food()

    def place_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in self.snake]
        self.food = random.choice(free)

    def on_key(self, event):
        dirs = {"Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0)}
        if event.keysym in dirs:
            d = dirs[event.keysym]
            # Ne dopusti okret za 180 stupnjeva
            if (d[0] + self.direction[0], d[1] + self.direction[1]) != (0, 0):
                self.next_dir = d
        elif event.keysym == "space" and not self.alive:
            self.reset()

    def tick(self):
        if self.alive:
            self.step()
        self.draw()
        self.root.after(SPEED_MS, self.tick)

    def step(self):
        self.direction = self.next_dir
        hx, hy = self.snake[0]
        head = (hx + self.direction[0], hy + self.direction[1])
        if (not (0 <= head[0] < COLS and 0 <= head[1] < ROWS)
                or head in self.snake[:-1]):
            self.alive = False
            self.best = max(self.best, self.score)
            return
        self.snake.insert(0, head)
        if head == self.food:
            self.score += 1
            self.place_food()
        else:
            self.snake.pop()

    def draw(self):
        c = self.canvas
        c.delete("all")
        fx, fy = self.food
        c.create_oval(fx * CELL + 4, fy * CELL + 4, (fx + 1) * CELL - 4,
                      (fy + 1) * CELL - 4, fill="#f38ba8", outline="")
        for i, (x, y) in enumerate(self.snake):
            color = "#a6e3a1" if i == 0 else "#40a02b"
            c.create_rectangle(x * CELL + 1, y * CELL + 1, (x + 1) * CELL - 1,
                               (y + 1) * CELL - 1, fill=color, outline="")
        c.create_text(8, 8, anchor="nw", fill="#cdd6f4", font=("Segoe UI", 12),
                      text=f"Bodovi: {self.score}   Rekord: {self.best}")
        if not self.alive:
            c.create_text(COLS * CELL // 2, ROWS * CELL // 2, fill="#cdd6f4",
                          font=("Segoe UI", 20, "bold"),
                          text="Kraj igre!\nSpace za novu igru", justify="center")


if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    Zmija(root)
    root.mainloop()
