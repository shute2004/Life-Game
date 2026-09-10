import os
import random
from typing import Mapping

import numpy as np

import config
from cell import Cell


DEFAULT_SPECIES_COUNTS: dict[str, int] = {
    config.SPECIES_PLANT: 800,
    config.SPECIES_HERBIVORE: 240,
    config.SPECIES_HUMAN: 60,
    config.SPECIES_CARNIVORE: 30,
}


class SimulationSetup:
    @staticmethod
    def ensure_log_directory(log_dir: str | None = None) -> str:
        resolved = log_dir or config.LOG_DIR
        os.makedirs(resolved, exist_ok=True)
        return resolved

    @classmethod
    def get_voice_log_filepaths(cls, log_dir: str | None = None) -> dict[str, str]:
        resolved = cls.ensure_log_directory(log_dir)
        return {
            config.SPECIES_HUMAN: os.path.join(resolved, "voice_log_human.txt"),
            config.SPECIES_HERBIVORE: os.path.join(resolved, "voice_log_herbivore.txt"),
            config.SPECIES_CARNIVORE: os.path.join(resolved, "voice_log_carnivore.txt"),
        }

    @classmethod
    def write_voice_log_headers(cls, log_dir: str | None = None) -> None:
        header = "Step,Speaker_ID,Speaker_X,Speaker_Y,Speaker_Voice,Actual_Speaker_State,Inferred_State_Data\n"
        for path in cls.get_voice_log_filepaths(log_dir).values():
            with open(path, "w", encoding="utf-8") as file:
                file.write(header)

    @staticmethod
    def _free_positions(occupied: set[tuple[int, int]]) -> list[tuple[int, int]]:
        return [
            (x, y)
            for x in range(config.GRID_W)
            for y in range(config.GRID_H)
            if (x, y) not in occupied
        ]

    @classmethod
    def _choose_plant_position(
        cls,
        env,
        occupied: set[tuple[int, int]],
        max_diagonal: float,
    ) -> tuple[int, int]:
        # Fast rejection sampling preserves the original volcano-distance bias.
        for _ in range(10_000):
            x = random.randint(0, config.GRID_W - 1)
            y = random.randint(0, config.GRID_H - 1)
            if (x, y) in occupied:
                continue
            distance = np.sqrt((x - env.base_cx) ** 2 + (y - env.base_cy) ** 2)
            probability = max(0.05, 1.0 - distance / max_diagonal)
            if random.random() < probability:
                return x, y

        # At very high occupancy, choose among the remaining cells while
        # retaining the same relative spatial preference instead of colliding.
        free = cls._free_positions(occupied)
        if not free:
            raise ValueError("Initial population exceeds available grid cells.")
        weights = [
            max(
                0.05,
                1.0
                - np.sqrt((x - env.base_cx) ** 2 + (y - env.base_cy) ** 2)
                / max_diagonal,
            )
            for x, y in free
        ]
        return random.choices(free, weights=weights, k=1)[0]

    @classmethod
    def _choose_clustered_position(
        cls,
        center: tuple[int, int],
        occupied: set[tuple[int, int]],
    ) -> tuple[int, int]:
        for _ in range(1_000):
            x = max(0, min(config.GRID_W - 1, int(random.gauss(center[0], 10.0))))
            y = max(0, min(config.GRID_H - 1, int(random.gauss(center[1], 10.0))))
            if (x, y) not in occupied:
                return x, y

        free = cls._free_positions(occupied)
        if not free:
            raise ValueError("Initial population exceeds available grid cells.")
        return min(
            free,
            key=lambda pos: (pos[0] - center[0]) ** 2 + (pos[1] - center[1]) ** 2,
        )

    @classmethod
    def spawn_initial_life(
        cls,
        env,
        next_id_start: int = 1,
        species_counts: Mapping[str, int] | None = None,
    ) -> tuple[list[Cell], int]:
        counts = dict(DEFAULT_SPECIES_COUNTS if species_counts is None else species_counts)
        unknown = set(counts) - set(DEFAULT_SPECIES_COUNTS)
        if unknown:
            raise ValueError(f"Unknown species in initial counts: {sorted(unknown)}")
        if any(not isinstance(count, int) or count < 0 for count in counts.values()):
            raise ValueError("Initial species counts must be non-negative integers.")

        for species in DEFAULT_SPECIES_COUNTS:
            counts.setdefault(species, 0)

        total_requested = sum(counts.values())
        capacity = config.GRID_W * config.GRID_H
        if total_requested > capacity:
            raise ValueError(
                f"Initial population ({total_requested}) exceeds grid capacity ({capacity})."
            )

        cells: list[Cell] = []
        occupied: set[tuple[int, int]] = set()
        next_id = next_id_start
        max_diagonal = float(np.sqrt(config.GRID_W**2 + config.GRID_H**2))

        cluster_centers: dict[str, list[tuple[int, int]]] = {}
        for species in [config.SPECIES_HUMAN, config.SPECIES_HERBIVORE, config.SPECIES_CARNIVORE]:
            center_count = 3 if species == config.SPECIES_HERBIVORE else 2
            cluster_centers[species] = [
                (
                    random.randint(15, config.GRID_W - 16),
                    random.randint(15, config.GRID_H - 16),
                )
                for _ in range(center_count)
            ]

        for species, count in counts.items():
            for _ in range(count):
                if species == config.SPECIES_PLANT:
                    x, y = cls._choose_plant_position(env, occupied, max_diagonal)
                else:
                    center = random.choice(cluster_centers[species])
                    x, y = cls._choose_clustered_position(center, occupied)

                occupied.add((x, y))
                cell = Cell(
                    cell_id=next_id,
                    x=x,
                    y=y,
                    energy=random.uniform(20.0, 50.0) if species == config.SPECIES_PLANT else 40.0,
                    metabolism=0.5,
                    repro_threshold=30.0,
                    mutation_rate=0.1,
                    mutation_magnitude=0.1,
                    w_food=random.uniform(0.1, 2.0),
                    w_stress=random.uniform(-2.0, -0.1),
                    w_density=random.uniform(-0.5, 0.5),
                    w_memory=random.uniform(-1.0, 1.0),
                    v_mating=random.uniform(-1.0, 1.0),
                    v_altruism=random.uniform(-1.0, 1.0),
                    give_fraction=random.uniform(0.0, 0.5),
                    immunity=random.uniform(0.0, 0.5),
                    give_gold_fraction=random.uniform(0.0, 0.5),
                    w_gold=random.uniform(-1.0, 1.0),
                    sex="XX" if random.random() < 0.5 else "XY",
                    species=species,
                    age=config.ADULT_AGE,
                    is_adult=True,
                )
                cell.voice = ""
                cells.append(cell)
                next_id += 1

        assert len(occupied) == len(cells)
        return cells, next_id
