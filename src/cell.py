from typing import Dict, Optional, Tuple

import config


class Cell:
    """Individual state, genes, social memory, and association memory."""

    def __init__(
        self,
        cell_id: int,
        x: int,
        y: int,
        energy: float,
        metabolism: float,
        repro_threshold: float,
        mutation_rate: float,
        mutation_magnitude: float,
        w_food: float,
        w_stress: float,
        w_density: float,
        w_memory: float,
        v_mating: float,
        v_altruism: float,
        give_fraction: float,
        immunity: float,
        give_gold_fraction: float,
        w_gold: float,
        sex: str,
        species: str,
        age: int = 80,
        is_adult: bool = True,
    ) -> None:
        self.id = cell_id
        self.x = x
        self.y = y
        self.energy = energy
        self.sex = sex
        self.species = species
        self.gold = 0.0

        self.age = age
        self.is_adult = is_adult
        self.is_dead = False
        self.fatigue = 0.0
        self.is_sleeping = False
        self.poison_timer = 0
        self.repro_cooldown = 0
        self.voice = ""

        self.genes: Dict[str, float] = {
            "metabolism": metabolism,
            "repro_threshold": repro_threshold,
            "mutation_rate": mutation_rate,
            "mutation_magnitude": mutation_magnitude,
            "w_food": w_food,
            "w_stress": w_stress,
            "w_density": w_density,
            "w_memory": w_memory,
            "v_mating": v_mating,
            "v_altruism": v_altruism,
            "give_fraction": give_fraction,
            "immunity": immunity,
            "give_gold_fraction": give_gold_fraction,
            "w_gold": w_gold,
        }

        self.social_memory: Dict[int, float] = {}
        self.association_memory: Dict[str, Dict[str, float]] = {}
        self.stored_assets: Dict[Tuple[int, int], Dict[str, float]] = {}

    def get_physical_weight(self) -> float:
        return self.gold * config.WEIGHT_FACTOR_GOLD + self.energy * config.WEIGHT_FACTOR_ENERGY

    def get_color(self) -> Tuple[int, int, int]:
        r_base = max(50.0, min(255.0, (self.genes["w_density"] + 5.0) * 25.5))
        g_base = max(50.0, min(255.0, (self.genes["w_food"] + 5.0) * 25.5))
        b_base = max(50.0, min(255.0, (-self.genes["w_stress"] + 5.0) * 25.5))
        ratio = min(1.0, max(0.0, self.energy) / self.genes["repro_threshold"])
        return int(r_base * ratio), int(g_base * ratio), int(b_base * ratio)

    def apply_environmental_damage(self, stress: float) -> None:
        import random

        if stress <= 0.05 or random.random() >= stress * 0.02:
            return
        target_gene = random.choice(list(self.genes.keys()))
        value = self.genes[target_gene]
        value += value * random.uniform(-0.05, 0.05)
        min_value, max_value = config.LIMITS[target_gene]
        self.genes[target_gene] = max(min_value, min(max_value, value))

    def learn_association(self, event_a: str, event_b: str) -> None:
        if not event_a or not event_b:
            return
        self.association_memory.setdefault(event_a, {})
        self.association_memory[event_a][event_b] = self.association_memory[event_a].get(event_b, 0.0) + 1.0

    def infer_association(self, event_a: str) -> Optional[str]:
        if event_a not in self.association_memory or not self.association_memory[event_a]:
            return None
        return max(self.association_memory[event_a], key=self.association_memory[event_a].get)

    def add_gold(self, amount: float) -> None:
        self.gold += amount

    def update_memory(self, target_id: int, delta: float) -> None:
        current = self.social_memory.get(target_id, 0.0)
        self.social_memory[target_id] = max(-10.0, min(10.0, current + delta))
        if len(self.social_memory) > config.MEMORY_LIMIT:
            forget = min(self.social_memory, key=lambda key: abs(self.social_memory[key]))
            self.social_memory.pop(forget, None)
