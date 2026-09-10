import random
from typing import Dict, List, Optional, Set, Tuple

import config
from cell import Cell
from cell_genetics import CellGenetics
from cell_navigator import CellNavigator


class InteractionMate:
    @classmethod
    def mate_process(
        cls,
        female: Cell,
        male_candidates: List[Cell],
        env,
        occupied_positions: Set[Tuple[int, int]],
        pos_to_cell: Dict[Tuple[int, int], Cell],
        next_id_gen,
    ) -> Tuple[List[Cell], Optional[Cell], bool, int, bool]:
        """Process one mating interaction.

        Returns ``(children, dead_female, attempted, litter_size,
        cross_species_attempt)``. ``attempted`` means that a partner was
        selected and interaction costs were paid; it does not imply offspring
        were produced.
        """
        best_partner: Optional[Cell] = None
        best_score = -float("inf")
        for male in male_candidates:
            score = CellNavigator.evaluate_position(
                female,
                male.x,
                male.y,
                env,
                occupied_positions,
                pos_to_cell,
                partner_id=male.id,
            )
            if score > best_score:
                best_score = score
                best_partner = male

        if best_partner is None:
            return [], None, False, 0, False

        female_cooldown = 300 if female.species == config.SPECIES_HUMAN else 250 if female.species == config.SPECIES_CARNIVORE else 150
        male_cooldown = 300 if best_partner.species == config.SPECIES_HUMAN else 250 if best_partner.species == config.SPECIES_CARNIVORE else 150
        female.repro_cooldown = female_cooldown
        best_partner.repro_cooldown = male_cooldown
        female.energy *= 0.90
        best_partner.energy *= 0.90
        female.fatigue += 2.0
        best_partner.fatigue += 2.0

        female_prior = female.social_memory.get(best_partner.id, 0.0)
        male_prior = best_partner.social_memory.get(female.id, 0.0)
        if female_prior > 0.0:
            female.update_memory(best_partner.id, female_prior * 0.2)
        if male_prior > 0.0:
            best_partner.update_memory(female.id, male_prior * 0.2)

        if female.species != best_partner.species:
            return [], None, True, 0, True

        child_count = random.choices([1, 2, 3, 4, 5], weights=config.LITTER_PROBS, k=1)[0]
        maternal_death = random.random() < config.MATERNAL_DEATH_PROBS[child_count - 1]

        child_energy = female.energy / (child_count + 1)
        female.energy = child_energy

        candidates: List[Tuple[int, int]] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = female.x + dx, female.y + dy
                if 0 <= nx < config.GRID_W and 0 <= ny < config.GRID_H and (nx, ny) not in occupied_positions:
                    candidates.append((nx, ny))

        scored = [
            (
                CellNavigator.evaluate_position(
                    female, cx, cy, env, occupied_positions, pos_to_cell
                ),
                (cx, cy),
            )
            for cx, cy in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)

        placed: List[Cell] = []
        stress = float(env.stress_grid[female.x, female.y])
        for _, position in scored[:child_count]:
            child = CellGenetics.crossover(
                female,
                best_partner,
                next_id_gen(),
                position[0],
                position[1],
                child_energy,
                stress,
            )
            if child is not None:
                child.repro_cooldown = female_cooldown
                placed.append(child)
                occupied_positions.add(position)
                pos_to_cell[position] = child

        if len(placed) < child_count:
            female.energy += (child_count - len(placed)) * child_energy

        female.update_memory(
            best_partner.id,
            female.genes["v_mating"] * female.social_memory.get(best_partner.id, 0.0),
        )
        best_partner.update_memory(
            female.id,
            best_partner.genes["v_mating"] * best_partner.social_memory.get(female.id, 0.0),
        )
        for child in placed:
            child.update_memory(female.id, 5.0)
            child.update_memory(best_partner.id, 5.0)
            female.update_memory(child.id, 5.0)

        maternal_dead_cell = None
        if maternal_death:
            female.is_dead = True
            env.add_dropped_gold(female.x, female.y, female.gold)
            env.add_meat_food(female.x, female.y, 5.0 + female.energy)
            occupied_positions.discard((female.x, female.y))
            pos_to_cell.pop((female.x, female.y), None)
            maternal_dead_cell = female

        return placed, maternal_dead_cell, True, child_count, False
