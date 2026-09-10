import random

import numpy as np

import config
from cell import Cell


class SimulationGeneAnalyzer:
    @staticmethod
    def calculate_max_gene_distance(
        cells: list[Cell], env
    ) -> tuple[float, tuple[int, int], tuple[int, int], float, float]:
        if len(cells) < 2:
            return 0.0, (0, 0), (0, 0), 0.0, 0.0

        sampled_cells = random.sample(cells, min(100, len(cells)))
        gene_keys = [
            "metabolism", "repro_threshold", "mutation_rate", "mutation_magnitude",
            "w_food", "w_stress", "w_density", "w_memory", "v_mating", "v_altruism",
            "give_fraction", "immunity", "give_gold_fraction", "w_gold",
        ]

        normalized: list[tuple[np.ndarray, Cell]] = []
        for cell in sampled_cells:
            values = []
            for key in gene_keys:
                minimum, maximum = config.LIMITS[key]
                span = maximum - minimum
                values.append((cell.genes[key] - minimum) / span if span > 0.0 else 0.0)
            normalized.append((np.array(values, dtype=np.float32), cell))

        max_distance = -1.0
        best_pair: tuple[Cell, Cell] | None = None
        for i, (vec_a, cell_a) in enumerate(normalized):
            for vec_b, cell_b in normalized[i + 1:]:
                distance = float(np.linalg.norm(vec_a - vec_b))
                if distance > max_distance:
                    max_distance = distance
                    best_pair = (cell_a, cell_b)

        if best_pair is None:
            return 0.0, (0, 0), (0, 0), 0.0, 0.0

        cell_a, cell_b = best_pair
        return (
            max_distance,
            (cell_a.x, cell_a.y),
            (cell_b.x, cell_b.y),
            float(env.stress_grid[cell_a.x, cell_a.y]),
            float(env.stress_grid[cell_b.x, cell_b.y]),
        )
