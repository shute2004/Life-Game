import pytest

import config
from cell import Cell
from environment import Environment
from interaction_mate import InteractionMate


def make_cell(cell_id: int, x: int, y: int, species: str, sex: str) -> Cell:
    return Cell(
        cell_id=cell_id,
        x=x,
        y=y,
        energy=100.0,
        metabolism=0.5,
        repro_threshold=30.0,
        mutation_rate=0.1,
        mutation_magnitude=0.1,
        w_food=1.0,
        w_stress=-1.0,
        w_density=0.0,
        w_memory=0.0,
        v_mating=0.0,
        v_altruism=0.0,
        give_fraction=0.0,
        immunity=0.0,
        give_gold_fraction=0.0,
        w_gold=0.0,
        sex=sex,
        species=species,
        age=config.ADULT_AGE,
        is_adult=True,
    )


def test_cross_species_selection_is_an_explicit_zero_child_attempt() -> None:
    env = Environment()
    female = make_cell(1, 20, 20, config.SPECIES_HUMAN, "XX")
    male = make_cell(2, 21, 20, config.SPECIES_HERBIVORE, "XY")
    occupied = {(20, 20), (21, 20)}
    positions = {(20, 20): female, (21, 20): male}

    children, dead_female, success, litter_size = InteractionMate.mate_process(
        female,
        [male],
        env,
        occupied,
        positions,
        lambda: 3,
    )

    assert success is True
    assert children == []
    assert dead_female is None
    assert litter_size == 0
    assert female.energy == pytest.approx(90.0)
    assert male.energy == pytest.approx(90.0)
    assert female.repro_cooldown == 300
    assert male.repro_cooldown == 150


def test_no_birth_space_is_not_classified_as_hybrid_attempt() -> None:
    env = Environment()
    female = make_cell(1, 20, 20, config.SPECIES_HUMAN, "XX")
    male = make_cell(2, 21, 20, config.SPECIES_HUMAN, "XY")
    occupied = {
        (20 + dx, 20 + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
    }
    positions = {(20, 20): female, (21, 20): male}

    children, dead_female, success, litter_size = InteractionMate.mate_process(
        female,
        [male],
        env,
        occupied,
        positions,
        lambda: 3,
    )

    assert success is False
    assert children == []
    assert dead_female is None
    assert litter_size == 0
