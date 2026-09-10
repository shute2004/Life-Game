from typing import Dict, Tuple

WIDTH: int = 800
HEIGHT: int = 600
CELL_SIZE: int = 4
GRID_W: int = WIDTH // CELL_SIZE
GRID_H: int = HEIGHT // CELL_SIZE
FPS: int = 60

LOG_DIR: str = "log"

COLOR_BG: Tuple[int, int, int] = (10, 10, 10)
COLOR_CELL: Tuple[int, int, int] = (255, 255, 255)

SPECIES_PLANT: str = "Plant"
SPECIES_HERBIVORE: str = "Herbivore"
SPECIES_CARNIVORE: str = "Carnivore"
SPECIES_HUMAN: str = "Human"

VOICE_CHARSET: list[str] = ["0", "1", "a", "b", "e", "n", "s", "d", " "]

MAX_GOLD_IN_WORLD: float = 1000.0
GOLD_MINE_RADIUS: float = 10.0

LIMITS: Dict[str, Tuple[float, float]] = {
    "metabolism": (0.1, 2.0),
    "repro_threshold": (15.0, 60.0),
    "mutation_rate": (0.0, 1.0),
    "mutation_magnitude": (0.0, 1.0),
    "w_food": (-5.0, 5.0),
    "w_stress": (-5.0, 5.0),
    "w_density": (-5.0, 5.0),
    "w_memory": (-5.0, 5.0),
    "v_mating": (-1.0, 1.0),
    "v_altruism": (-1.0, 1.0),
    "give_fraction": (0.0, 0.8),
    "immunity": (0.0, 1.0),
    "give_gold_fraction": (0.0, 1.0),
    "w_gold": (-5.0, 5.0),
}

MEMORY_LIMIT: int = 30

LITTER_PROBS: Tuple[float, float, float, float, float] = (0.90, 0.07, 0.02, 0.008, 0.002)
MATERNAL_DEATH_PROBS: Tuple[float, float, float, float, float] = (0.002, 0.008, 0.02, 0.05, 0.10)

DRIFT_SPEED: float = 0.005
DRIFT_RANGE_X: float = 0.20
SEASON_SPEED: float = 0.01
SEASON_AMPLITUDE: float = 0.50
BASE_FOOD_GEN_PLAIN: float = 0.05

ADULT_AGE: int = 80

FATIGUE_LIMIT: float = 100.0
FATIGUE_GAIN_MOVE: float = 2.0
FATIGUE_GAIN_COMBAT: float = 25.0
FATIGUE_RECOVERY_SLEEP: float = 8.0

DECAY_RATE_PLANT: float = 0.005
DECAY_RATE_MEAT: float = 0.08
ENERGY_DENSITY_PLANT: float = 2.0
ENERGY_DENSITY_MEAT: float = 10.0

COMBAT_PENALTY_LOSER: float = 0.50

WEIGHT_FACTOR_GOLD: float = 2.0
WEIGHT_FACTOR_ENERGY: float = 0.1
WEIGHT_DECAY_RECOVERY_BETA: float = 0.05
OWNER_SENSING_RADIUS: int = 3
