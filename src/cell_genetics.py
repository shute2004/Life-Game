import random
from typing import Dict, Optional

import numpy as np

import config
from cell import Cell


class CellGenetics:
    @staticmethod
    def calculate_cosine_similarity(cell_a: Cell, cell_b: Cell) -> float:
        gene_keys = [
            "metabolism", "repro_threshold", "mutation_rate", "mutation_magnitude",
            "w_food", "w_stress", "w_density", "w_memory", "v_mating", "v_altruism",
            "give_fraction", "immunity", "give_gold_fraction", "w_gold",
        ]
        vec_a = np.array([cell_a.genes[key] for key in gene_keys], dtype=np.float32)
        vec_b = np.array([cell_b.genes[key] for key in gene_keys], dtype=np.float32)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a <= 0.0 or norm_b <= 0.0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    @staticmethod
    def get_kuru_death_probability(similarity: float) -> float:
        clamped = max(-1.0, min(1.0, similarity))
        return 0.05 + (clamped + 1.0) * 0.075

    @classmethod
    def crossover(
        cls,
        parent_a: Cell,
        parent_b: Cell,
        child_id: int,
        cx: int,
        cy: int,
        child_energy: float,
        parent_stress: float,
    ) -> Optional[Cell]:
        if parent_a.species != parent_b.species:
            return None

        gene_keys = [
            "metabolism", "repro_threshold", "mutation_rate", "mutation_magnitude",
            "w_food", "w_stress", "w_density", "w_memory", "v_mating", "v_altruism",
            "give_fraction", "immunity", "give_gold_fraction", "w_gold",
        ]
        child_genes: Dict[str, float] = {
            key: parent_a.genes[key] if random.random() < 0.5 else parent_b.genes[key]
            for key in gene_keys
        }
        child_sex = "XX" if random.random() < 0.5 else "XY"

        mutation_rate = child_genes["mutation_rate"] + parent_stress * 0.5
        mutation_magnitude = child_genes["mutation_magnitude"] * (1.0 + parent_stress)
        for key in gene_keys:
            if random.random() < mutation_rate:
                value = child_genes[key]
                child_genes[key] = value + random.uniform(-1.0, 1.0) * value * mutation_magnitude

        for key in gene_keys:
            minimum, maximum = config.LIMITS[key]
            child_genes[key] = max(minimum, min(maximum, child_genes[key]))

        return Cell(
            cell_id=child_id,
            x=cx,
            y=cy,
            energy=child_energy,
            metabolism=child_genes["metabolism"],
            repro_threshold=child_genes["repro_threshold"],
            mutation_rate=child_genes["mutation_rate"],
            mutation_magnitude=child_genes["mutation_magnitude"],
            w_food=child_genes["w_food"],
            w_stress=child_genes["w_stress"],
            w_density=child_genes["w_density"],
            w_memory=child_genes["w_memory"],
            v_mating=child_genes["v_mating"],
            v_altruism=child_genes["v_altruism"],
            give_fraction=child_genes["give_fraction"],
            immunity=child_genes["immunity"],
            give_gold_fraction=child_genes["give_gold_fraction"],
            w_gold=child_genes["w_gold"],
            sex=child_sex,
            species=parent_a.species,
            age=0,
            is_adult=False,
        )
