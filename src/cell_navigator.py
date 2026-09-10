from typing import Dict, Optional, Set, Tuple

import config
from cell import Cell
from config import GRID_H, GRID_W


class CellNavigator:
    @staticmethod
    def evaluate_position(
        cell: Cell,
        tx: int,
        ty: int,
        env,
        occupied_positions: Set[Tuple[int, int]],
        pos_to_cell: Dict[Tuple[int, int], Cell],
        partner_id: Optional[int] = None,
    ) -> float:
        density = 0
        gold_social_score = 0.0
        association_social_score = 0.0

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) in occupied_positions:
                    density += 1
                    neighbor = pos_to_cell.get((nx, ny))
                    if neighbor is None or neighbor == cell or neighbor.is_dead:
                        continue
                    gold_social_score += cell.genes["w_gold"] * neighbor.gold
                    if neighbor.voice:
                        predicted = cell.infer_association(f"voice:{neighbor.voice}")
                        if predicted == "target_state:starving":
                            association_social_score += cell.genes["w_stress"] * 2.0
                        elif predicted == "target_state:danger":
                            association_social_score += cell.genes["w_stress"] * 1.5
                        elif predicted == "target_state:mating_ready":
                            association_social_score += cell.genes["w_food"] * 1.5

        risk_penalty = 0.0
        if (env.food_grid[tx, ty] > 0.0 or env.gold_grid[tx, ty] > 0.0) and (tx, ty) in env.owner_grid:
            owner_id = env.owner_grid[(tx, ty)]
            if owner_id != cell.id:
                owner_cell: Optional[Cell] = None
                for other in pos_to_cell.values():
                    if other.id == owner_id:
                        if (
                            not other.is_dead
                            and not other.is_sleeping
                            and max(abs(other.x - tx), abs(other.y - ty)) <= config.OWNER_SENSING_RADIUS
                        ):
                            owner_cell = other
                        break
                if owner_cell is not None:
                    thief_power = max(0.01, cell.energy * cell.genes["metabolism"])
                    owner_power = max(0.01, owner_cell.energy * owner_cell.genes["metabolism"])
                    risk_penalty = (owner_power / thief_power) * 2.0

        score = (
            cell.genes["w_food"] * float(env.food_grid[tx, ty])
            + cell.genes["w_stress"] * float(env.stress_grid[tx, ty])
            + cell.genes["w_density"] * density
            - risk_penalty
            + gold_social_score
            + association_social_score
        )
        if partner_id is not None:
            score += cell.genes["w_memory"] * cell.social_memory.get(partner_id, 0.0)
        return score

    @classmethod
    def choose_best_action(
        cls,
        cell: Cell,
        env,
        occupied_positions: Set[Tuple[int, int]],
        pos_to_cell: Dict[Tuple[int, int], Cell],
        check_reproduce: bool,
    ) -> Optional[Tuple[int, int]]:
        candidates: list[Tuple[int, int]] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = cell.x + dx, cell.y + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in occupied_positions:
                    candidates.append((nx, ny))
        if not check_reproduce:
            candidates.append((cell.x, cell.y))
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda pos: cls.evaluate_position(
                cell, pos[0], pos[1], env, occupied_positions, pos_to_cell
            ),
        )

    @classmethod
    def get_move_pos(
        cls,
        cell: Cell,
        env,
        occupied_positions: Set[Tuple[int, int]],
        pos_to_cell: Dict[Tuple[int, int], Cell],
    ) -> Optional[Tuple[int, int]]:
        if not cell.is_adult or cell.is_sleeping or cell.species == config.SPECIES_PLANT:
            return None
        best = cls.choose_best_action(cell, env, occupied_positions, pos_to_cell, check_reproduce=False)
        return None if best is None or best == (cell.x, cell.y) else best
