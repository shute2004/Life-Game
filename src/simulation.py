import os
import random
from typing import Mapping

import numpy as np

import config
from cell import Cell
from cell_navigator import CellNavigator
from cell_vitality import CellVitality
from environment import Environment
from interaction_combat import InteractionCombat
from interaction_give import InteractionGive
from interaction_mate import InteractionMate
from simulation_gene_analyzer import SimulationGeneAnalyzer
from simulation_setup import SimulationSetup
from simulation_theft_detector import SimulationTheftDetector
from simulation_voice_analyzer import SimulationVoiceAnalyzer
from stats_logger import StatsLogger


class Simulation:
    """Coordinate the environment, organisms, interactions, and audit output."""

    def __init__(
        self,
        log_filename: str = "simulation_log.csv",
        *,
        seed: int | None = None,
        species_counts: Mapping[str, int] | None = None,
        log_dir: str | None = None,
    ) -> None:
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.log_dir = SimulationSetup.ensure_log_directory(log_dir)
        self.env = Environment()
        self.stats_logger = StatsLogger(os.path.join(self.log_dir, log_filename))
        self.voice_log_paths = SimulationSetup.get_voice_log_filepaths(self.log_dir)

        self.cells: list[Cell] = []
        self.step_count = 0
        self.max_gene_dist = 0.0
        self.next_id = 1
        self.trackers = self._new_trackers()

        self.stats_logger.write_header()
        SimulationSetup.write_voice_log_headers(self.log_dir)
        self.env.spawn_initial_food()
        self.cells, self.next_id = SimulationSetup.spawn_initial_life(
            self.env,
            self.next_id,
            species_counts=species_counts,
        )

    @staticmethod
    def _new_trackers() -> dict:
        return {
            "litter_sizes": [],
            "maternal_deaths": 0,
            "starvation_deaths": 0,
            "crossover_count": 0,
            "gives_count": 0,
            "gives_amount": 0.0,
            "gives_gold_count": 0,
            "gives_gold_amount": 0.0,
            "gold_exchange_count": 0,
            "loots_count": 0,
            "loots_amount": 0.0,
            "defenses_count": 0,
            "combat_deaths": 0,
            "prion_deaths": 0,
            "kuru_deaths": 0,
            "hybrid_attempts": 0,
            "total_mine_gold": 0.0,
            "conversation_count": 0,
            "Store_Assets_Count_Step": 0,
            "Store_Assets_Amount_Step": 0.0,
            "Theft_Count_Step": 0,
            "Retaliation_Count_Step": 0,
            "Intimidation_Retreat_Count_Step": 0,
            "Weight_Recovery_Decay_Step": 0.0,
        }

    def _detect_and_log_theft(self, cell: Cell, tx: int, ty: int, recovered_amount: float) -> None:
        if recovered_amount <= 0.0:
            return
        owner_id = self.env.owner_grid.get((tx, ty))
        if owner_id is None or owner_id == cell.id:
            return

        self.trackers["Theft_Count_Step"] += 1
        for other in self.cells:
            if (
                other.id == owner_id
                and not other.is_dead
                and not other.is_sleeping
                and max(abs(other.x - tx), abs(other.y - ty)) <= config.OWNER_SENSING_RADIUS
            ):
                self.trackers["Retaliation_Count_Step"] += 1
                break

    def step(self) -> None:
        self.step_count += 1
        self.env.update_environment(self.step_count)
        self.env.update_food_generation(self.step_count)
        season_factor = self.env.get_season_factor(self.step_count)

        for cell in self.cells:
            if not cell.is_dead and cell.is_sleeping and cell.species != config.SPECIES_PLANT:
                weight = cell.get_physical_weight()
                recovery = max(
                    1.0,
                    config.FATIGUE_RECOVERY_SLEEP - config.WEIGHT_DECAY_RECOVERY_BETA * weight,
                )
                decay = config.FATIGUE_RECOVERY_SLEEP - recovery
                if decay > 0.0:
                    self.trackers["Weight_Recovery_Decay_Step"] += decay

            CellVitality.update_energy_and_fatigue(cell)
            if cell.species == config.SPECIES_PLANT:
                CellVitality.photosynthesize(cell, self.env.stress_grid, season_factor)
            if cell.repro_cooldown > 0:
                cell.repro_cooldown -= 1

        random.shuffle(self.cells)
        pos_to_cell = {(cell.x, cell.y): cell for cell in self.cells if not cell.is_dead}

        for cell in self.cells:
            if not cell.is_dead and cell.species == config.SPECIES_HUMAN:
                old_gold = cell.gold
                old_energy = cell.energy
                CellVitality.try_store_assets_before_sleep(cell, self.env, pos_to_cell)
                if cell.is_sleeping and (cell.gold < old_gold or cell.energy < old_energy):
                    self.trackers["Store_Assets_Count_Step"] += 1
                    self.trackers["Store_Assets_Amount_Step"] += (
                        old_gold - cell.gold + old_energy - cell.energy
                    )

        pos_to_cell = {(cell.x, cell.y): cell for cell in self.cells if not cell.is_dead}
        occupied_positions = set(pos_to_cell)

        for cell in self.cells:
            if cell.is_dead or cell.is_sleeping:
                continue
            if cell.species == config.SPECIES_PLANT and random.random() >= 0.1:
                continue
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = cell.x + dx, cell.y + dy
                    if 0 <= nx < config.GRID_W and 0 <= ny < config.GRID_H:
                        neighbor = pos_to_cell.get((nx, ny))
                        if (
                            neighbor is not None
                            and neighbor != cell
                            and not neighbor.is_dead
                            and not neighbor.is_sleeping
                            and neighbor.voice
                        ):
                            actual_state = SimulationVoiceAnalyzer.determine_exteriors_state(
                                neighbor, self.env
                            )
                            cell.learn_association(
                                f"voice:{neighbor.voice}",
                                f"target_state:{actual_state}",
                            )

        surviving_cells: list[Cell] = []
        new_cells: list[Cell] = []
        max_diagonal = float(np.sqrt(config.GRID_W**2 + config.GRID_H**2))

        for cell in self.cells:
            if cell.is_dead:
                continue
            if (cell.x, cell.y) not in occupied_positions or pos_to_cell.get((cell.x, cell.y)) != cell:
                continue

            if cell.energy <= 0.0:
                cell.is_dead = True
                self.env.add_dropped_gold(cell.x, cell.y, cell.gold)
                self.env.add_meat_food(cell.x, cell.y, max(0.0, cell.energy) + 5.0)
                occupied_positions.discard((cell.x, cell.y))
                pos_to_cell.pop((cell.x, cell.y), None)
                self.trackers["starvation_deaths"] += 1
                continue

            stress = float(self.env.stress_grid[cell.x, cell.y])
            cell.apply_environmental_damage(stress)
            mated = False

            if cell.species == config.SPECIES_PLANT:
                if cell.energy >= cell.genes["repro_threshold"] and cell.repro_cooldown == 0:
                    distance = np.sqrt(
                        (cell.x - self.env.base_cx) ** 2 + (cell.y - self.env.base_cy) ** 2
                    )
                    settle_probability = 0.01 * max(0.05, 1.0 - distance / max_diagonal)
                    if random.random() < settle_probability:
                        candidates = [
                            (cell.x + dx, cell.y + dy)
                            for dx in (-1, 0, 1)
                            for dy in (-1, 0, 1)
                            if (dx != 0 or dy != 0)
                            and 0 <= cell.x + dx < config.GRID_W
                            and 0 <= cell.y + dy < config.GRID_H
                            and (cell.x + dx, cell.y + dy) not in occupied_positions
                        ]
                        if candidates:
                            rx, ry = random.choice(candidates)
                            child_energy = cell.energy / 2.0
                            cell.energy /= 2.0
                            cell.repro_cooldown = 600
                            child = Cell(
                                cell_id=self.next_id,
                                x=rx,
                                y=ry,
                                energy=child_energy,
                                metabolism=cell.genes["metabolism"],
                                repro_threshold=cell.genes["repro_threshold"],
                                mutation_rate=cell.genes["mutation_rate"],
                                mutation_magnitude=cell.genes["mutation_magnitude"],
                                w_food=cell.genes["w_food"],
                                w_stress=cell.genes["w_stress"],
                                w_density=cell.genes["w_density"],
                                w_memory=cell.genes["w_memory"],
                                v_mating=cell.genes["v_mating"],
                                v_altruism=cell.genes["v_altruism"],
                                give_fraction=cell.genes["give_fraction"],
                                immunity=cell.genes["immunity"],
                                give_gold_fraction=cell.genes["give_gold_fraction"],
                                w_gold=cell.genes["w_gold"],
                                sex="XX",
                                species=config.SPECIES_PLANT,
                                age=0,
                                is_adult=False,
                            )
                            self.next_id += 1
                            child.repro_cooldown = 600
                            new_cells.append(child)
                            occupied_positions.add((rx, ry))
                            pos_to_cell[(rx, ry)] = child
                            self.trackers["crossover_count"] += 1

            elif not cell.is_sleeping:
                distance = np.sqrt(
                    (cell.x - self.env.base_cx) ** 2 + (cell.y - self.env.base_cy) ** 2
                )
                if distance <= config.GOLD_MINE_RADIUS:
                    gained = self.env.mine_gold(0.1)
                    cell.add_gold(gained)
                    self.trackers["total_mine_gold"] += gained

                gives, give_amount, gold_gives, gold_amount, exchanges = InteractionGive.give_process(
                    cell, pos_to_cell
                )
                self.trackers["gives_count"] += gives
                self.trackers["gives_amount"] += give_amount
                self.trackers["gives_gold_count"] += gold_gives
                self.trackers["gives_gold_amount"] += gold_amount
                self.trackers["gold_exchange_count"] += exchanges

                old_energy_combat = cell.energy
                loots, loot_amount, defenses, deaths, prion, kuru = InteractionCombat.combat_process(
                    cell, pos_to_cell, occupied_positions, self.env
                )
                self.trackers["loots_count"] += loots
                self.trackers["loots_amount"] += loot_amount
                self.trackers["defenses_count"] += defenses
                self.trackers["combat_deaths"] += deaths
                self.trackers["prion_deaths"] += prion
                self.trackers["kuru_deaths"] += kuru

                if (
                    not cell.is_dead
                    and loots == 0
                    and deaths == 0
                    and old_energy_combat > 0.0
                    and abs(cell.energy - old_energy_combat * 0.90) < 0.01
                ):
                    self.trackers["Intimidation_Retreat_Count_Step"] += 1

                if cell.is_dead:
                    continue

                if (
                    cell.is_adult
                    and cell.sex == "XX"
                    and cell.energy >= cell.genes["repro_threshold"]
                    and cell.repro_cooldown == 0
                ):
                    male_candidates = [
                        pos_to_cell[(cell.x + dx, cell.y + dy)]
                        for dx in (-1, 0, 1)
                        for dy in (-1, 0, 1)
                        if (dx != 0 or dy != 0)
                        and 0 <= cell.x + dx < config.GRID_W
                        and 0 <= cell.y + dy < config.GRID_H
                        and (cell.x + dx, cell.y + dy) in occupied_positions
                        and pos_to_cell[(cell.x + dx, cell.y + dy)].sex == "XY"
                        and pos_to_cell[(cell.x + dx, cell.y + dy)].is_adult
                        and not pos_to_cell[(cell.x + dx, cell.y + dy)].is_sleeping
                        and pos_to_cell[(cell.x + dx, cell.y + dy)].repro_cooldown == 0
                        and pos_to_cell[(cell.x + dx, cell.y + dy)].energy
                        >= pos_to_cell[(cell.x + dx, cell.y + dy)].genes["repro_threshold"] / 2.0
                    ]
                    if male_candidates:
                        def next_id_gen() -> int:
                            child_id = self.next_id
                            self.next_id += 1
                            return child_id

                        children, dead_female, success, litter_size = InteractionMate.mate_process(
                            cell,
                            male_candidates,
                            self.env,
                            occupied_positions,
                            pos_to_cell,
                            next_id_gen,
                        )
                        if success:
                            if children:
                                new_cells.extend(children)
                                self.trackers["litter_sizes"].append(litter_size)
                                self.trackers["crossover_count"] += 1
                                mated = True
                            else:
                                self.trackers["hybrid_attempts"] += 1
                            if dead_female is not None:
                                self.trackers["maternal_deaths"] += 1
                                continue

                if not mated:
                    move_pos = CellNavigator.get_move_pos(
                        cell, self.env, occupied_positions, pos_to_cell
                    )
                    if move_pos is not None:
                        old_pos = (cell.x, cell.y)
                        occupied_positions.discard(old_pos)
                        occupied_positions.add(move_pos)
                        pos_to_cell.pop(old_pos, None)
                        pos_to_cell[move_pos] = cell
                        cell.x, cell.y = move_pos
                        cell.fatigue += config.FATIGUE_GAIN_MOVE

                tx, ty = cell.x, cell.y
                gold_recovered = CellVitality.collect_gold_from_ground(cell, self.env)
                if gold_recovered > 0.0:
                    self._detect_and_log_theft(cell, tx, ty, gold_recovered)
                    SimulationTheftDetector.check_theft_and_retaliate(
                        cell,
                        pos_to_cell,
                        tx,
                        ty,
                        self.env,
                        occupied_positions,
                        self.trackers,
                    )
                if cell.is_dead:
                    continue

                food_recovered = CellVitality.feed_and_check_poison(cell, self.env)
                if food_recovered > 0.0:
                    self._detect_and_log_theft(cell, tx, ty, food_recovered)
                    SimulationTheftDetector.check_theft_and_retaliate(
                        cell,
                        pos_to_cell,
                        tx,
                        ty,
                        self.env,
                        occupied_positions,
                        self.trackers,
                    )
                if cell.is_dead:
                    continue

            emit_probability = 0.02
            if cell.energy < 15.0:
                emit_probability += 0.20
            if float(self.env.stress_grid[cell.x, cell.y]) > 0.5:
                emit_probability += 0.20
            if cell.is_adult and cell.energy >= cell.genes["repro_threshold"]:
                emit_probability += 0.15

            if (
                random.random() < emit_probability
                and not cell.is_sleeping
                and not cell.is_dead
                and cell.species != config.SPECIES_PLANT
            ):
                cell.voice = "".join(random.choices(config.VOICE_CHARSET, k=random.randint(1, 8)))
            else:
                cell.voice = ""

            SimulationVoiceAnalyzer.check_and_log_conversations(
                self.step_count,
                cell,
                pos_to_cell,
                self.voice_log_paths,
                self.trackers,
                self.env,
            )
            surviving_cells.append(cell)

        self.cells = [cell for cell in surviving_cells + new_cells if not cell.is_dead]
        if self.step_count % 10 == 0:
            self.log_stats()

    def log_stats(self) -> None:
        max_dist, pos_a, pos_b, stress_a, stress_b = SimulationGeneAnalyzer.calculate_max_gene_distance(
            self.cells, self.env
        )
        self.max_gene_dist = max_dist
        self.stats_logger.log_statistics(
            self.step_count,
            self.cells,
            self.env,
            max_dist,
            pos_a,
            pos_b,
            stress_a,
            stress_b,
            self.trackers,
        )
        self.trackers = self._new_trackers()

    def summary(self) -> dict[str, int | float | None]:
        gold_held = float(sum(cell.gold for cell in self.cells))
        gold_ground = float(np.sum(self.env.gold_grid))
        return {
            "seed": self.seed,
            "step": self.step_count,
            "population": len(self.cells),
            "human": sum(cell.species == config.SPECIES_HUMAN for cell in self.cells),
            "herbivore": sum(cell.species == config.SPECIES_HERBIVORE for cell in self.cells),
            "carnivore": sum(cell.species == config.SPECIES_CARNIVORE for cell in self.cells),
            "plant": sum(cell.species == config.SPECIES_PLANT for cell in self.cells),
            "total_food": float(np.sum(self.env.food_grid)),
            "gold_held": gold_held,
            "gold_ground": gold_ground,
            "gold_reserve": float(self.env.remaining_gold),
            "total_gold": gold_held + gold_ground + float(self.env.remaining_gold),
            "max_gene_distance": self.max_gene_dist,
        }
