import random
from typing import Dict, Tuple

import numpy as np

import config
from config import GRID_H, GRID_W


class Environment:
    """2D resources, stress, decay, dropped assets, and ownership metadata."""

    def __init__(self) -> None:
        self.base_cx: float = GRID_W / 2
        self.base_cy: float = GRID_H / 2

        self.food_grid = np.zeros((GRID_W, GRID_H), dtype=np.float32)
        self.stress_grid = np.zeros((GRID_W, GRID_H), dtype=np.float32)
        self.food_type_grid = np.zeros((GRID_W, GRID_H), dtype=np.float32)
        self.decay_grid = np.zeros((GRID_W, GRID_H), dtype=np.float32)
        self.gold_grid = np.zeros((GRID_W, GRID_H), dtype=np.float32)
        self.remaining_gold: float = config.MAX_GOLD_IN_WORLD
        self.owner_grid: Dict[Tuple[int, int], int] = {}

        self.setup_stress_map(self.base_cx, self.base_cy)

    def setup_stress_map(self, cx: float, cy: float) -> None:
        max_dist = float(np.sqrt(GRID_W**2 + GRID_H**2))
        radius = max_dist * 0.35
        x, y = np.ogrid[:GRID_W, :GRID_H]
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        self.stress_grid = np.clip(1.0 - (dist / radius), 0.0, 1.0).astype(np.float32)

    def spawn_initial_food(self) -> None:
        for _ in range((GRID_W * GRID_H) // 2):
            rx = random.randint(0, GRID_W - 1)
            ry = random.randint(0, GRID_H - 1)
            self.food_grid[rx, ry] += 5.0
            self.food_type_grid[rx, ry] = 0.0
            self.decay_grid[rx, ry] = 0.0

    def mine_gold(self, amount: float) -> float:
        if self.remaining_gold <= 0.0:
            return 0.0
        gained = min(amount, self.remaining_gold)
        self.remaining_gold -= gained
        return gained

    def add_dropped_gold(self, x: int, y: int, amount: float) -> None:
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            self.gold_grid[x, y] += amount

    def add_meat_food(self, x: int, y: int, amount: float) -> None:
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return
        current_food = self.food_grid[x, y]
        new_food = current_food + amount
        if new_food > 0.0:
            self.food_type_grid[x, y] = (
                current_food * self.food_type_grid[x, y] + amount
            ) / new_food
            self.decay_grid[x, y] = (
                current_food * self.decay_grid[x, y]
            ) / new_food
        self.food_grid[x, y] = new_food

    def add_stored_resource(
        self,
        x: int,
        y: int,
        owner_id: int,
        food_amount: float,
        gold_amount: float,
        food_type: float = 0.5,
        decay: float = 0.0,
    ) -> None:
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return

        if food_amount > 0.0:
            current_food = self.food_grid[x, y]
            new_food = current_food + food_amount
            if new_food > 0.0:
                self.food_type_grid[x, y] = (
                    current_food * self.food_type_grid[x, y] + food_amount * food_type
                ) / new_food
                self.decay_grid[x, y] = (
                    current_food * self.decay_grid[x, y] + food_amount * decay
                ) / new_food
            self.food_grid[x, y] = new_food

        if gold_amount > 0.0:
            self.gold_grid[x, y] += gold_amount

        if self.food_grid[x, y] > 0.0 or self.gold_grid[x, y] > 0.0:
            self.owner_grid[(x, y)] = owner_id

    def check_and_clean_owner(self, x: int, y: int) -> None:
        if (x, y) in self.owner_grid:
            if self.food_grid[x, y] <= 0.0 and self.gold_grid[x, y] <= 0.0:
                self.owner_grid.pop((x, y), None)

    def update_environment(self, step_count: int) -> None:
        offset_x = np.sin(step_count * config.DRIFT_SPEED) * (GRID_W * config.DRIFT_RANGE_X)
        self.setup_stress_map(self.base_cx + offset_x, self.base_cy)

    def get_season_factor(self, step_count: int) -> float:
        return float(1.0 + np.sin(step_count * config.SEASON_SPEED) * config.SEASON_AMPLITUDE)

    def update_food_generation(self, step_count: int) -> None:
        season_factor = self.get_season_factor(step_count)
        gen_amount = (config.BASE_FOOD_GEN_PLAIN + self.stress_grid * 0.15) * season_factor

        new_food = self.food_grid + gen_amount
        self.food_type_grid = np.where(
            new_food > 0.0,
            (self.food_grid * self.food_type_grid) / np.maximum(1e-5, new_food),
            0.0,
        ).astype(np.float32)
        self.decay_grid = np.where(
            new_food > 0.0,
            (self.food_grid * self.decay_grid) / np.maximum(1e-5, new_food),
            0.0,
        ).astype(np.float32)
        self.food_grid = new_food

        active_mask = self.food_grid > 0.0
        if np.any(active_mask):
            delta_decay = (
                (1.0 - self.food_type_grid) * config.DECAY_RATE_PLANT
                + self.food_type_grid * config.DECAY_RATE_MEAT
            )
            self.decay_grid[active_mask] += delta_decay[active_mask]
            self.decay_grid = np.clip(self.decay_grid, 0.0, 1.0)
