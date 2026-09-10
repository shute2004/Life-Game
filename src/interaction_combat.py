import random
from typing import Dict, List, Optional, Set, Tuple

import config
from cell import Cell
from cell_genetics import CellGenetics


class InteractionCombat:
    @classmethod
    def resolve_combat(
        cls,
        attacker: Cell,
        defender: Cell,
        env,
        occupied_positions: Set[Tuple[int, int]],
        pos_to_cell: Dict[Tuple[int, int], Cell],
    ) -> Tuple[bool, bool, bool, int, int]:
        is_draw = False
        attacker_dead = False
        defender_dead = False
        prion_deaths = 0
        kuru_deaths = 0
        plant_prey = defender.species == config.SPECIES_PLANT

        attacker_power = max(0.01, attacker.energy * attacker.genes["metabolism"])
        defender_power = max(0.01, defender.energy * defender.genes["metabolism"])
        power_ratio = attacker_power / (attacker_power + defender_power)

        if 0.4 <= power_ratio <= 0.6 and not plant_prey and random.random() < 0.5:
            is_draw = True
            attacker_loss = attacker.energy * 0.10
            defender_loss = defender.energy * 0.10
            attacker.energy -= attacker_loss
            defender.energy -= defender_loss
            env.add_meat_food(attacker.x, attacker.y, attacker_loss + defender_loss)
            attacker.fatigue += min(50.0, 25.0 + 50.0 / max(0.1, attacker.genes["metabolism"]))
            defender.fatigue += min(50.0, 25.0 + 50.0 / max(0.1, defender.genes["metabolism"]))

            candidates: List[Tuple[int, int]] = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = attacker.x + dx, attacker.y + dy
                    if 0 <= nx < config.GRID_W and 0 <= ny < config.GRID_H and (nx, ny) not in occupied_positions:
                        candidates.append((nx, ny))
            if candidates:
                escape = random.choice(candidates)
                old = (attacker.x, attacker.y)
                occupied_positions.discard(old)
                occupied_positions.add(escape)
                pos_to_cell.pop(old, None)
                pos_to_cell[escape] = attacker
                attacker.x, attacker.y = escape
            return is_draw, attacker_dead, defender_dead, prion_deaths, kuru_deaths

        win_probability = 1.0 if plant_prey else power_ratio
        attacker_win_fatigue = max(5.0, 25.0 - attacker.genes["metabolism"] * 10.0)
        attacker_lose_fatigue = min(50.0, 25.0 + 50.0 / max(0.1, attacker.genes["metabolism"]))
        defender_win_fatigue = max(5.0, 25.0 - defender.genes["metabolism"] * 10.0)

        if random.random() < win_probability:
            defender_dead = True
            loot_energy = defender.energy * 0.8
            defender.is_dead = True
            attacker.fatigue += attacker_win_fatigue
            env.add_dropped_gold(defender.x, defender.y, defender.gold)
            env.add_meat_food(defender.x, defender.y, defender.energy * 0.2 + 5.0)
            occupied_positions.discard((defender.x, defender.y))
            pos_to_cell.pop((defender.x, defender.y), None)

            if attacker.species == defender.species and not plant_prey:
                if attacker.species == config.SPECIES_HUMAN:
                    attacker.is_dead = True
                    attacker_dead = True
                    env.add_dropped_gold(attacker.x, attacker.y, attacker.gold)
                    env.add_meat_food(attacker.x, attacker.y, attacker.energy + 5.0)
                    occupied_positions.discard((attacker.x, attacker.y))
                    pos_to_cell.pop((attacker.x, attacker.y), None)
                    prion_deaths += 1
                    return is_draw, attacker_dead, defender_dead, prion_deaths, kuru_deaths

                if attacker.species == config.SPECIES_CARNIVORE:
                    similarity = CellGenetics.calculate_cosine_similarity(attacker, defender)
                    if random.random() < CellGenetics.get_kuru_death_probability(similarity):
                        attacker.is_dead = True
                        attacker_dead = True
                        env.add_dropped_gold(attacker.x, attacker.y, attacker.gold)
                        env.add_meat_food(attacker.x, attacker.y, attacker.energy + 5.0)
                        occupied_positions.discard((attacker.x, attacker.y))
                        pos_to_cell.pop((attacker.x, attacker.y), None)
                        kuru_deaths += 1
                        return is_draw, attacker_dead, defender_dead, prion_deaths, kuru_deaths

            attacker.energy += loot_energy
            if not plant_prey:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        relative = pos_to_cell.get((defender.x + dx, defender.y + dy))
                        if (
                            relative is not None
                            and relative not in {attacker, defender}
                            and not relative.is_dead
                            and relative.social_memory.get(defender.id, 0.0) >= 5.0
                        ):
                            relative.update_memory(attacker.id, -20.0)
        else:
            attacker.fatigue += attacker_lose_fatigue
            if not plant_prey:
                defender.fatigue += defender_win_fatigue
            loss = attacker.energy * config.COMBAT_PENALTY_LOSER
            attacker.energy -= loss
            env.add_meat_food(attacker.x, attacker.y, loss)
            if not defender.is_dead:
                defender.update_memory(attacker.id, -20.0)

        return is_draw, attacker_dead, defender_dead, prion_deaths, kuru_deaths

    @classmethod
    def combat_process(
        cls,
        cell: Cell,
        pos_to_cell: Dict[Tuple[int, int], Cell],
        occupied_positions: Set[Tuple[int, int]],
        env,
    ) -> Tuple[int, float, int, int, int, int]:
        loots_count = 0
        loots_amount = 0.0
        defenses_count = 0
        combat_deaths = 0
        prion_deaths = 0
        kuru_deaths = 0

        if cell.species == config.SPECIES_PLANT or cell.energy >= cell.genes["repro_threshold"]:
            return loots_count, loots_amount, defenses_count, combat_deaths, prion_deaths, kuru_deaths

        best_target: Optional[Cell] = None
        best_score = -float("inf")
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                neighbor = pos_to_cell.get((cell.x + dx, cell.y + dy))
                if neighbor is None or neighbor == cell or neighbor.is_dead:
                    continue
                if cell.species == config.SPECIES_HERBIVORE and neighbor.species != config.SPECIES_PLANT:
                    continue
                if cell.species == config.SPECIES_CARNIVORE and neighbor.species == config.SPECIES_PLANT:
                    continue
                memory = cell.social_memory.get(neighbor.id, 0.0)
                score = -cell.genes["v_altruism"] * (1.0 - memory)
                if score > 0.0 and score > best_score:
                    best_score = score
                    best_target = neighbor

        if best_target is None:
            return loots_count, loots_amount, defenses_count, combat_deaths, prion_deaths, kuru_deaths

        combat_target = best_target
        if best_target.species != config.SPECIES_PLANT:
            defender: Optional[Cell] = None
            defender_power = -float("inf")
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    guardian = pos_to_cell.get((best_target.x + dx, best_target.y + dy))
                    if (
                        guardian is not None
                        and guardian not in {cell, best_target}
                        and not guardian.is_dead
                        and guardian.social_memory.get(best_target.id, 0.0) > 5.0
                    ):
                        power = guardian.energy * guardian.genes["metabolism"]
                        if power > defender_power:
                            defender_power = power
                            defender = guardian
            if defender is not None:
                combat_target = defender
                defenses_count += 1

        _, attacker_dead, defender_dead, prion, kuru = cls.resolve_combat(
            cell, combat_target, env, occupied_positions, pos_to_cell
        )
        prion_deaths += prion
        kuru_deaths += kuru
        if defender_dead:
            loots_count += 1
            loots_amount += combat_target.energy * 0.8
            combat_deaths += 1
        if attacker_dead:
            combat_deaths += 1
        if not best_target.is_dead:
            best_target.update_memory(cell.id, -20.0)

        return loots_count, loots_amount, defenses_count, combat_deaths, prion_deaths, kuru_deaths

    @classmethod
    def trigger_immediate_retaliation(
        cls,
        owner: Cell,
        thief: Cell,
        env,
        occupied_positions: Set[Tuple[int, int]],
        pos_to_cell: Dict[Tuple[int, int], Cell],
    ) -> Tuple[bool, int, int, int]:
        owner.update_memory(thief.id, -20.0)
        thief.update_memory(owner.id, -20.0)
        is_draw, owner_dead, thief_dead, prion, kuru = cls.resolve_combat(
            owner, thief, env, occupied_positions, pos_to_cell
        )
        return is_draw, int(owner_dead) + int(thief_dead), prion, kuru
