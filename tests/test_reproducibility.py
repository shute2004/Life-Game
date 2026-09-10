from pathlib import Path

import pytest

import config
from simulation import Simulation


SMALL_COUNTS = {
    config.SPECIES_PLANT: 10,
    config.SPECIES_HERBIVORE: 4,
    config.SPECIES_HUMAN: 3,
    config.SPECIES_CARNIVORE: 2,
}


def run_snapshot(tmp_path: Path, seed: int) -> tuple:
    simulation = Simulation(
        seed=seed,
        species_counts=SMALL_COUNTS,
        log_dir=str(tmp_path / f"seed-{seed}"),
    )
    for _ in range(4):
        simulation.step()

    cells = tuple(
        sorted(
            (
                cell.id,
                cell.species,
                cell.sex,
                cell.x,
                cell.y,
                round(cell.energy, 8),
                round(cell.gold, 8),
                round(cell.fatigue, 8),
                tuple(sorted((key, round(value, 8)) for key, value in cell.genes.items())),
            )
            for cell in simulation.cells
        )
    )
    summary = simulation.summary()
    compact_summary = tuple(
        (key, round(value, 8) if isinstance(value, float) else value)
        for key, value in sorted(summary.items())
    )
    return cells, compact_summary


def test_same_seed_reproduces_same_state(tmp_path: Path) -> None:
    assert run_snapshot(tmp_path / "a", 17) == run_snapshot(tmp_path / "b", 17)


def test_different_seed_changes_state(tmp_path: Path) -> None:
    assert run_snapshot(tmp_path / "a", 17) != run_snapshot(tmp_path / "b", 18)


def test_initial_species_counts_are_injectable(tmp_path: Path) -> None:
    simulation = Simulation(
        seed=5,
        species_counts=SMALL_COUNTS,
        log_dir=str(tmp_path / "counts"),
    )
    summary = simulation.summary()
    assert summary["population"] == sum(SMALL_COUNTS.values())
    assert summary["plant"] == 10
    assert summary["herbivore"] == 4
    assert summary["human"] == 3
    assert summary["carnivore"] == 2


def test_gold_is_conserved_across_steps(tmp_path: Path) -> None:
    simulation = Simulation(
        seed=23,
        species_counts=SMALL_COUNTS,
        log_dir=str(tmp_path / "gold"),
    )
    for _ in range(12):
        simulation.step()
    assert simulation.summary()["total_gold"] == pytest.approx(config.MAX_GOLD_IN_WORLD, abs=1e-4)
