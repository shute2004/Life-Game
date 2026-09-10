import csv
import os
from typing import Any, Dict, Tuple

import numpy as np

import config
from cell import Cell


class StatsLogger:
    """Append compact ecological, genetic, and economic audit metrics to CSV."""

    FIELDS = [
        "step",
        "population",
        "human",
        "herbivore",
        "carnivore",
        "plant",
        "total_food",
        "total_gold",
        "gold_held",
        "gold_ground",
        "gold_reserve",
        "avg_energy",
        "avg_fatigue",
        "max_gene_distance",
        "starvation_deaths",
        "combat_deaths",
        "maternal_deaths",
        "crossovers",
        "gives_count",
        "gold_exchanges",
        "theft_count",
        "retaliation_count",
        "conversations",
    ]

    def __init__(self, log_filepath: str = "simulation_log.csv") -> None:
        self.log_filepath = log_filepath
        parent = os.path.dirname(log_filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def write_header(self) -> None:
        with open(self.log_filepath, "w", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=self.FIELDS).writeheader()

    def log_statistics(
        self,
        step_count: int,
        cells: list[Cell],
        env,
        max_gene_dist: float,
        pos_a: Tuple[int, int],
        pos_b: Tuple[int, int],
        stress_a: float,
        stress_b: float,
        trackers: Dict[str, Any],
    ) -> None:
        del pos_a, pos_b, stress_a, stress_b

        gold_held = float(sum(cell.gold for cell in cells))
        gold_ground = float(np.sum(env.gold_grid))
        gold_reserve = float(env.remaining_gold)
        row = {
            "step": step_count,
            "population": len(cells),
            "human": sum(cell.species == config.SPECIES_HUMAN for cell in cells),
            "herbivore": sum(cell.species == config.SPECIES_HERBIVORE for cell in cells),
            "carnivore": sum(cell.species == config.SPECIES_CARNIVORE for cell in cells),
            "plant": sum(cell.species == config.SPECIES_PLANT for cell in cells),
            "total_food": f"{float(np.sum(env.food_grid)):.6f}",
            "total_gold": f"{gold_held + gold_ground + gold_reserve:.6f}",
            "gold_held": f"{gold_held:.6f}",
            "gold_ground": f"{gold_ground:.6f}",
            "gold_reserve": f"{gold_reserve:.6f}",
            "avg_energy": f"{float(np.mean([cell.energy for cell in cells])) if cells else 0.0:.6f}",
            "avg_fatigue": f"{float(np.mean([cell.fatigue for cell in cells])) if cells else 0.0:.6f}",
            "max_gene_distance": f"{max_gene_dist:.6f}",
            "starvation_deaths": trackers.get("starvation_deaths", 0),
            "combat_deaths": trackers.get("combat_deaths", 0),
            "maternal_deaths": trackers.get("maternal_deaths", 0),
            "crossovers": trackers.get("crossover_count", 0),
            "gives_count": trackers.get("gives_count", 0),
            "gold_exchanges": trackers.get("gold_exchange_count", 0),
            "theft_count": trackers.get("Theft_Count_Step", 0),
            "retaliation_count": trackers.get("Retaliation_Count_Step", 0),
            "conversations": trackers.get("conversation_count", 0),
        }

        with open(self.log_filepath, "a", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=self.FIELDS).writerow(row)
