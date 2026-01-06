"""Simple Pygame grid editor.

Controls:
 - Left click: draw (set cell ON)
 - Right click: erase (set cell OFF)
 - Middle click: toggle cell
 - R: generate warehouse layout
 - C: clear grid
 - Q or ESC: quit
"""

from __future__ import annotations

import random

import pygame

WIDTH, HEIGHT = 1280, 720
CELL = 20
FPS = 120

BG = (200, 200, 200)
WALL = (100, 100, 100)
GRID = (0, 0, 0)

COLS = WIDTH // CELL
ROWS = HEIGHT // CELL


class Grid:
    def __init__(self, cols: int = COLS, rows: int = ROWS, cell: int = CELL):
        self.cols, self.rows, self.cell = cols, rows, cell
        self.cells: list[list[bool]] = [[False] * cols for _ in range(rows)]

    def clear(self) -> None:
        empty = [False] * self.cols
        for row in self.cells:
            row[:] = empty

    def _set_cell(self, c: int, r: int, value: bool) -> None:
        if 0 <= c < self.cols and 0 <= r < self.rows:
            self.cells[r][c] = value

    def set_at_pixel(self, x: int, y: int, value: bool) -> None:
        self._set_cell(x // self.cell, y // self.cell, value)

    def toggle_at_pixel(self, x: int, y: int) -> None:
        c, r = x // self.cell, y // self.cell
        if 0 <= c < self.cols and 0 <= r < self.rows:
            self.cells[r][c] = not self.cells[r][c]

    def randomize(self, pillar_prob: float = 0.05) -> None:
        """Warehouse-style layout: shelves + aisles + cross-aisles + sparse pillars."""
        self.clear()

        shelf = max(1, self.cols // 40)
        aisle = max(2, self.cols // 8)
        cross = max(4, self.rows // 10)

        # Vertical shelf blocks
        for start in range(0, self.cols, shelf + aisle):
            for c in range(start, min(start + shelf, self.cols)):
                for r in range(self.rows):
                    self.cells[r][c] = True

        # 2-cell-thick cross-aisles (connect aisles)
        empty = [False] * self.cols
        for r in range(0, self.rows, cross):
            if r < self.rows:
                self.cells[r][:] = empty
            if r + 1 < self.rows:
                self.cells[r + 1][:] = empty

        # Pillars/obstacles inside aisles
        if pillar_prob > 0:
            for row in self.cells:
                for c, filled in enumerate(row):
                    if not filled and random.random() < pillar_prob:
                        row[c] = True

        # 2-cell-wide openings through shelf columns
        if self.rows >= 3:
            threshold = int(self.rows * 0.70)
            shelf_cols = [
                c
                for c in range(self.cols)
                if sum(self.cells[r][c] for r in range(self.rows)) >= threshold
            ]
            if shelf_cols:
                for _ in range(max(1, len(shelf_cols) // 3)):
                    c = random.choice(shelf_cols)
                    r = random.randint(1, self.rows - 2)
                    for rr in (r - 1, r, r + 1):
                        for cc in (c, c + 1):
                            if 0 <= cc < self.cols:
                                self.cells[rr][cc] = False

    def draw_walls(self, surface: pygame.Surface, color: tuple[int, int, int] = WALL) -> None:
        cs = self.cell
        for r, row in enumerate(self.cells):
            y = r * cs
            for c, filled in enumerate(row):
                if filled:
                    pygame.draw.rect(surface, color, (c * cs, y, cs, cs))


def build_grid_overlay() -> pygame.Surface:
    overlay = pygame.Surface((WIDTH, HEIGHT), flags=pygame.SRCALPHA)
    for x in range(0, WIDTH, CELL):
        pygame.draw.line(overlay, GRID, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, CELL):
        pygame.draw.line(overlay, GRID, (0, y), (WIDTH, y), 1)
    return overlay


def handle_events(grid: Grid) -> bool:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return False

        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_q, pygame.K_ESCAPE):
                return False
            if e.key == pygame.K_r:
                grid.randomize()
            elif e.key == pygame.K_c:
                grid.clear()

        elif e.type == pygame.MOUSEBUTTONDOWN:
            x, y = e.pos
            if e.button == 1:
                grid.set_at_pixel(x, y, True)
            elif e.button == 3:
                grid.set_at_pixel(x, y, False)
            elif e.button == 2:
                grid.toggle_at_pixel(x, y)

    return True


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    grid = Grid()
    overlay = build_grid_overlay()
    grid.randomize(pillar_prob=0.15)

    while handle_events(grid):
        screen.fill(BG)
        grid.draw_walls(screen)
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()