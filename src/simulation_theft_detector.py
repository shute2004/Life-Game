from typing import Dict, Set, Tuple

import config
from cell import Cell
from interaction_combat import InteractionCombat


class SimulationTheftDetector:
    @classmethod
    def check_theft_and_retaliate(
        cls,
        thief: Cell,
        pos_to_cell: Dict[Tuple[int, int], Cell],
        target_x: int,
        target_y: int,
        env,
        occupied_positions: Set[Tuple[int, int]],
        trackers: dict,
    ) -> None:
        owner_id = env.owner_grid.get((target_x, target_y))
        if owner_id is None or owner_id == thief.id:
            return

        owner_cell = None
        for other in pos_to_cell.values():
            if other.id == owner_id:
                if (
                    not other.is_dead
                    and not other.is_sleeping
                    and max(abs(other.x - target_x), abs(other.y - target_y))
                    <= config.OWNER_SENSING_RADIUS
                ):
                    owner_cell = other
                break

        if owner_cell is None:
            return

        _, deaths, prion, kuru = InteractionCombat.trigger_immediate_retaliation(
            owner=owner_cell,
            thief=thief,
            env=env,
            occupied_positions=occupied_positions,
            pos_to_cell=pos_to_cell,
        )
        trackers["combat_deaths"] += deaths
        trackers["prion_deaths"] += prion
        trackers["kuru_deaths"] += kuru
