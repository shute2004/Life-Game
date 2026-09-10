from typing import Dict, Tuple

import config
from cell import Cell


class InteractionGive:
    @classmethod
    def give_process(
        cls,
        cell: Cell,
        pos_to_cell: Dict[Tuple[int, int], Cell],
    ) -> Tuple[int, float, int, float, int]:
        gives_count = 0
        gives_amount = 0.0
        gives_gold_count = 0
        gives_gold_amount = 0.0
        gold_exchange_count = 0

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = cell.x + dx, cell.y + dy
                if not (0 <= nx < config.GRID_W and 0 <= ny < config.GRID_H):
                    continue
                neighbor = pos_to_cell.get((nx, ny))
                if neighbor is None or neighbor == cell or neighbor.is_dead:
                    continue

                energy_give = cell.energy * cell.genes["give_fraction"]
                can_give_energy = energy_give > 0.0 and cell.energy > energy_give
                gold_give = cell.gold * cell.genes["give_gold_fraction"]
                can_give_gold = gold_give > 0.0 and cell.gold >= gold_give
                if not (can_give_energy or can_give_gold):
                    continue

                memory = cell.social_memory.get(neighbor.id, 0.0)
                child_bonus = 2.0 if not neighbor.is_adult else 0.0
                motivation = cell.genes["v_altruism"] * (memory + child_bonus)
                if motivation <= 0.0:
                    continue

                if can_give_energy:
                    cell.energy -= energy_give
                    neighbor.energy += energy_give
                    gives_count += 1
                    gives_amount += energy_give

                if can_give_gold:
                    cell.gold -= gold_give
                    neighbor.gold += gold_give
                    gives_gold_count += 1
                    gives_gold_amount += gold_give

                    reverse_motivation = neighbor.genes["v_altruism"] * neighbor.social_memory.get(cell.id, 0.0)
                    energy_back = neighbor.energy * neighbor.genes["give_fraction"]
                    if reverse_motivation > 0.0 and energy_back > 0.0 and neighbor.energy > energy_back:
                        neighbor.energy -= energy_back
                        cell.energy += energy_back
                        gives_count += 1
                        gives_amount += energy_back
                        gold_exchange_count += 1

                cell.fatigue += 1.0
                neighbor.fatigue += 1.0
                cell.update_memory(neighbor.id, cell.genes["v_altruism"] * memory)
                neighbor.update_memory(cell.id, 0.5 * energy_give if can_give_energy else 0.5)

                for witness_dx in (-1, 0, 1):
                    for witness_dy in (-1, 0, 1):
                        if witness_dx == 0 and witness_dy == 0:
                            continue
                        witness_pos = (neighbor.x + witness_dx, neighbor.y + witness_dy)
                        other = pos_to_cell.get(witness_pos)
                        if other is not None and other not in {cell, neighbor} and not other.is_dead:
                            neighbor.update_memory(other.id, 0.5)

        return gives_count, gives_amount, gives_gold_count, gives_gold_amount, gold_exchange_count
