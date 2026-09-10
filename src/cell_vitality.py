import random

import config
from cell import Cell


class CellVitality:
    @staticmethod
    def grow(cell: Cell) -> None:
        if not cell.is_adult:
            cell.age += 1
            if cell.age >= config.ADULT_AGE:
                cell.is_adult = True
        if cell.poison_timer > 0:
            cell.poison_timer -= 1

    @classmethod
    def update_energy_and_fatigue(cls, cell: Cell) -> None:
        cls.grow(cell)
        if cell.poison_timer > 0:
            cell.is_sleeping = True

        base_metabolism = cell.genes["metabolism"]
        if cell.species == config.SPECIES_PLANT:
            base_metabolism *= 0.1
        if not cell.is_adult:
            base_metabolism *= 0.5

        if cell.is_sleeping:
            cell.energy -= base_metabolism * 0.5
            weight = cell.get_physical_weight()
            recovery = max(
                1.0,
                config.FATIGUE_RECOVERY_SLEEP - config.WEIGHT_DECAY_RECOVERY_BETA * weight,
            )
            cell.fatigue -= recovery
        else:
            cell.energy -= base_metabolism
            cell.fatigue -= 0.5

        if cell.fatigue <= 0.01:
            cell.fatigue = 0.0
        elif cell.fatigue > config.FATIGUE_LIMIT:
            cell.fatigue = config.FATIGUE_LIMIT

        if cell.is_sleeping:
            if cell.fatigue <= 0.0 and cell.poison_timer <= 0:
                cell.is_sleeping = False
        elif cell.fatigue >= 80.0:
            cell.is_sleeping = True

    @classmethod
    def try_store_assets_before_sleep(cls, cell: Cell, env, pos_to_cell: dict) -> None:
        if cell.species != config.SPECIES_HUMAN or cell.is_sleeping or not cell.is_adult:
            return
        if cell.fatigue < 75.0:
            return

        has_risk_neighbor = False
        radius = config.OWNER_SENSING_RADIUS
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = cell.x + dx, cell.y + dy
                if 0 <= nx < config.GRID_W and 0 <= ny < config.GRID_H:
                    neighbor = pos_to_cell.get((nx, ny))
                    if neighbor is not None and neighbor != cell and not neighbor.is_dead:
                        bond = cell.social_memory.get(neighbor.id)
                        if bond is None or bond < 0.0:
                            has_risk_neighbor = True
                            break
            if has_risk_neighbor:
                break

        if not has_risk_neighbor or cell.fatigue >= 90.0:
            food_amount = cell.energy * 0.3
            gold_amount = cell.gold * 0.3
            if food_amount > 0.0 or gold_amount > 0.0:
                cell.energy -= food_amount
                cell.gold -= gold_amount
                env.add_stored_resource(
                    x=cell.x,
                    y=cell.y,
                    owner_id=cell.id,
                    food_amount=food_amount,
                    gold_amount=gold_amount,
                    food_type=0.5,
                    decay=0.0,
                )
                cell.stored_assets.setdefault((cell.x, cell.y), {"food": 0.0, "gold": 0.0})
                cell.stored_assets[(cell.x, cell.y)]["food"] += food_amount
                cell.stored_assets[(cell.x, cell.y)]["gold"] += gold_amount
                cell.is_sleeping = True

    @staticmethod
    def collect_gold_from_ground(cell: Cell, env) -> float:
        if not cell.is_adult or cell.is_sleeping or cell.species == config.SPECIES_PLANT:
            return 0.0
        amount = float(env.gold_grid[cell.x, cell.y])
        if amount > 0.0:
            cell.gold += amount
            env.gold_grid[cell.x, cell.y] = 0.0
            env.check_and_clean_owner(cell.x, cell.y)
            return amount
        return 0.0

    @staticmethod
    def photosynthesize(cell: Cell, stress_grid, season_factor: float) -> None:
        if cell.species == config.SPECIES_PLANT:
            stress = float(stress_grid[cell.x, cell.y])
            cell.energy += 2.0 * (1.0 - stress) * season_factor

    @staticmethod
    def feed_and_check_poison(cell: Cell, env) -> float:
        if not cell.is_adult or cell.is_sleeping or cell.species == config.SPECIES_PLANT:
            return 0.0

        food_available = float(env.food_grid[cell.x, cell.y])
        eat_amount = min(5.0, food_available)
        if eat_amount <= 0.0:
            return 0.0

        food_type = float(env.food_type_grid[cell.x, cell.y])
        density = (
            (1.0 - food_type) * config.ENERGY_DENSITY_PLANT
            + food_type * config.ENERGY_DENSITY_MEAT
        )
        cell.energy += eat_amount * density
        env.food_grid[cell.x, cell.y] = max(0.0, food_available - eat_amount)
        env.check_and_clean_owner(cell.x, cell.y)

        decay = float(env.decay_grid[cell.x, cell.y])
        if decay > 0.1:
            poison_probability = decay * (1.0 - cell.genes["immunity"])
            if random.random() < poison_probability:
                cell.energy *= 0.5
                cell.is_sleeping = True
                cell.poison_timer = 30
        return eat_amount
