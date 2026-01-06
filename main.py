"""Simple Pygame grid editor.

Controls:
 - Left click: draw (set cell ON)
 - Right click: erase (set cell OFF)
 - Middle click: toggle cell
 - R: generate warehouse layout
 - C: clear grid
 - G: toggle grid lines
 - Q or ESC: quit
"""

from __future__ import annotations

import random

import pygame

WIDTH, HEIGHT = 1280, 720
CELL = 20
FPS = 120

PANEL_W_TARGET = 260

BG = (200, 200, 200)
WALL = (100, 100, 100)
GRID = (0, 0, 0)

PANEL_BG = (230, 230, 230)
PANEL_FG = (40, 40, 40)
BTN_BG = (245, 245, 245)
BTN_HOVER = (235, 235, 235)
BTN_DISABLED = (210, 210, 210)

ROBOT = (255, 215, 0)
TARGET = (0, 180, 0)

# Grid uses the left area; panel uses the right.
COLS = (WIDTH - PANEL_W_TARGET) // CELL
ROWS = HEIGHT // CELL
GRID_W = COLS * CELL
PANEL_X = GRID_W
PANEL_W = WIDTH - GRID_W


class Grid:
    def __init__(self, cols: int = COLS, rows: int = ROWS, cell: int = CELL):
        self.cols, self.rows, self.cell = cols, rows, cell
        self.cells: list[list[bool]] = [[False] * cols for _ in range(rows)]
        self.robot: tuple[int, int] | None = None
        self.target: tuple[int, int] | None = None

    def clear(self) -> None:
        empty = [False] * self.cols
        for row in self.cells:
            row[:] = empty
        self.robot = None
        self.target = None

    def _is_marker(self, c: int, r: int) -> bool:
        return (self.robot == (c, r)) or (self.target == (c, r))

    def _set_cell(self, c: int, r: int, value: bool) -> None:
        if 0 <= c < self.cols and 0 <= r < self.rows:
            if value and self._is_marker(c, r):
                return
            self.cells[r][c] = value

    def set_at_pixel(self, x: int, y: int, value: bool) -> None:
        self._set_cell(x // self.cell, y // self.cell, value)

    def toggle_at_pixel(self, x: int, y: int) -> None:
        c, r = x // self.cell, y // self.cell
        if 0 <= c < self.cols and 0 <= r < self.rows:
            if self._is_marker(c, r):
                return
            self.cells[r][c] = not self.cells[r][c]

    def spawn_robot_and_target(self) -> None:
        free: list[tuple[int, int]] = [
            (c, r)
            for r in range(self.rows)
            for c in range(self.cols)
            if not self.cells[r][c]
        ]
        if not free:
            self.robot = None
            self.target = None
            return

        self.robot = random.choice(free)
        if len(free) == 1:
            self.target = None
            return

        free.remove(self.robot)
        self.target = random.choice(free)

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

        self.spawn_robot_and_target()

    def draw_walls(self, surface: pygame.Surface, color: tuple[int, int, int] = WALL) -> None:
        cs = self.cell
        for r, row in enumerate(self.cells):
            y = r * cs
            for c, filled in enumerate(row):
                if filled:
                    pygame.draw.rect(surface, color, (c * cs, y, cs, cs))

    def draw_markers(self, surface: pygame.Surface) -> None:
        cs = self.cell
        pad = max(2, cs // 6)

        if self.target is not None:
            c, r = self.target
            rect = pygame.Rect(c * cs + pad, r * cs + pad, cs - 2 * pad, cs - 2 * pad)
            pygame.draw.rect(surface, TARGET, rect, border_radius=6)

        if self.robot is not None:
            c, r = self.robot
            rect = pygame.Rect(c * cs + pad, r * cs + pad, cs - 2 * pad, cs - 2 * pad)
            pygame.draw.rect(surface, ROBOT, rect, border_radius=6)
            pygame.draw.rect(surface, GRID, rect, 1, border_radius=6)


def build_grid_overlay() -> pygame.Surface:
    overlay = pygame.Surface((GRID_W, HEIGHT), flags=pygame.SRCALPHA)
    for x in range(0, GRID_W + 1, CELL):
        pygame.draw.line(overlay, GRID, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, CELL):
        pygame.draw.line(overlay, GRID, (0, y), (GRID_W, y), 1)
    return overlay


def grid_label(show_grid: bool) -> str:
    return f"Grid: {'On' if show_grid else 'Off'} (G)"


class Button:
    def __init__(self, rect: pygame.Rect, label: str, on_click, *, enabled: bool = True):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.enabled = enabled

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, *, hover: bool) -> None:
        if not self.enabled:
            bg = BTN_DISABLED
        else:
            bg = BTN_HOVER if hover else BTN_BG

        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, GRID, self.rect, 1, border_radius=8)
        text = font.render(self.label, True, PANEL_FG)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_mouse_down(self, pos: tuple[int, int]) -> bool:
        if self.enabled and self.rect.collidepoint(pos):
            self.on_click()
            return True
        return False


class Slider:
    def __init__(
        self,
        rect: pygame.Rect,
        *,
        value: float,
        min_value: float,
        max_value: float,
        label: str,
    ):
        self.rect = rect
        self.value = value
        self.min = min_value
        self.max = max_value
        self.label = label
        self.dragging = False

    def _value_to_x(self) -> int:
        t = 0.0 if self.max == self.min else (self.value - self.min) / (self.max - self.min)
        t = max(0.0, min(1.0, t))
        return int(self.rect.x + t * self.rect.w)

    def _x_to_value(self, x: int) -> float:
        t = (x - self.rect.x) / max(1, self.rect.w)
        t = max(0.0, min(1.0, t))
        return self.min + t * (self.max - self.min)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        label = font.render(f"{self.label}: {self.value:.2f}", True, PANEL_FG)
        surface.blit(label, (self.rect.x, self.rect.y - 22))

        pygame.draw.rect(surface, BTN_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, GRID, self.rect, 1, border_radius=8)

        knob_x = self._value_to_x()
        knob = pygame.Rect(0, 0, 12, self.rect.h + 8)
        knob.center = (knob_x, self.rect.centery)
        pygame.draw.rect(surface, BTN_HOVER, knob, border_radius=6)
        pygame.draw.rect(surface, GRID, knob, 1, border_radius=6)

    def handle_event(self, e: pygame.event.Event) -> bool:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.dragging = True
            self.value = self._x_to_value(e.pos[0])
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.dragging:
            self.dragging = False
            return True
        if e.type == pygame.MOUSEMOTION and self.dragging:
            self.value = self._x_to_value(e.pos[0])
            return True
        return False


def build_ui(
    *,
    grid: Grid,
    initial_pillar_prob: float,
    show_grid: bool,
    on_toggle_grid,
) -> tuple[list[Button], Slider, Button]:
    pad = 14
    x = PANEL_X + pad
    w = PANEL_W - 2 * pad
    h = 44
    y = 50
    gap = 54

    grid_button = Button(pygame.Rect(x, y + 2 * gap, w, h), grid_label(show_grid), on_toggle_grid)
    buttons = [
        Button(pygame.Rect(x, y, w, h), "Generate (R)", lambda: None),
        Button(pygame.Rect(x, y + gap, w, h), "Clear (C)", grid.clear),
        grid_button,
        Button(pygame.Rect(x, y + 3 * gap, w, h), "Save (soon)", lambda: None, enabled=False),
        Button(pygame.Rect(x, y + 4 * gap, w, h), "Load (soon)", lambda: None, enabled=False),
    ]

    slider = Slider(
        pygame.Rect(x, 384, w, 20),
        value=initial_pillar_prob,
        min_value=0.0,
        max_value=0.25,
        label="Pillars",
    )

    # Patch in the real generate callback once slider exists.
    buttons[0].on_click = lambda: grid.randomize(pillar_prob=slider.value)
    return buttons, slider, grid_button


def handle_events(
    grid: Grid, buttons: list[Button], slider: Slider, *, on_toggle_grid
) -> bool:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return False

        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_q, pygame.K_ESCAPE):
                return False
            if e.key == pygame.K_r:
                grid.randomize(pillar_prob=slider.value)
            elif e.key == pygame.K_c:
                grid.clear()
            elif e.key == pygame.K_g:
                on_toggle_grid()

        if slider.handle_event(e):
            continue

        elif e.type == pygame.MOUSEBUTTONDOWN:
            x, y = e.pos
            if x >= PANEL_X:
                for b in buttons:
                    if b.handle_mouse_down(e.pos):
                        break
                continue
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

    font = pygame.font.SysFont(None, 22)
    title_font = pygame.font.SysFont(None, 26)

    grid = Grid()
    overlay = build_grid_overlay()
    show_grid = True

    def toggle_grid() -> None:
        nonlocal show_grid
        show_grid = not show_grid
        grid_button.label = grid_label(show_grid)

    buttons, slider, grid_button = build_ui(
        grid=grid,
        initial_pillar_prob=0.05,
        show_grid=show_grid,
        on_toggle_grid=toggle_grid,
    )
    grid.randomize(pillar_prob=slider.value)

    while handle_events(grid, buttons, slider, on_toggle_grid=toggle_grid):
        screen.fill(BG)
        grid.draw_walls(screen)
        grid.draw_markers(screen)
        if show_grid:
            screen.blit(overlay, (0, 0))

        # Panel
        pygame.draw.rect(screen, PANEL_BG, (PANEL_X, 0, PANEL_W, HEIGHT))
        pygame.draw.line(screen, GRID, (PANEL_X, 0), (PANEL_X, HEIGHT), 2)

        screen.blit(title_font.render("Controls", True, PANEL_FG), (PANEL_X + 14, 14))
        mx, my = pygame.mouse.get_pos()
        for b in buttons:
            b.draw(screen, font, hover=b.rect.collidepoint((mx, my)))
        slider.draw(screen, font)
        screen.blit(font.render("More tools soon...", True, PANEL_FG), (PANEL_X + 14, HEIGHT - 34))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
