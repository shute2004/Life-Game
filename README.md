# Life-Game

Life-Game is a bottom-up artificial-life simulation that explores how ecology, evolution, resource pressure, exchange, social memory, and simple communication can interact under local rules.

The project is not Conway's Game of Life. It models individual organisms with energy, fatigue, age, genes, mutation, movement preferences, reproduction, social memory, and species-specific behavior inside a changing 2D environment.

## Public snapshot

This repository is a cleaned source snapshot. Development archives, generated simulation logs, analysis images, `.DS_Store` files, and historical working documents are intentionally excluded.

The executable source is under `src/`.

Main subsystems:

- `environment.py` — food, decay, stress field, dropped resources, and finite gold reserve.
- `cell.py` / `cell_*` — organism state, genetics, vitality, learning, and navigation.
- `interaction_*` — mating, resource transfer, exchange, combat, and related social effects.
- `simulation.py` — orchestration of one simulation step.
- `stats_logger.py` — population, genetic, ecological, and economic audit metrics.
- `main.py` — Pygame visualization.
- `headless.py` — deterministic command-line runs for experiments and CI.

## Reproducibility

The engine uses both Python's `random` module and NumPy. `Simulation(seed=...)` seeds both sources before environment and population initialization.

Initial species counts are configurable for tests and small experiments without changing the default full simulation:

- Plant: 800
- Herbivore: 240
- Human: 60
- Carnivore: 30

Initial placement enforces a one-cell-one-agent invariant. Clustered animal placement retries occupied coordinates and falls back to the nearest free coordinate if necessary; initialization rejects a population larger than the grid capacity.

A headless run can be reproduced with the same seed:

```bash
python src/headless.py --seed 7 --steps 100 --log-dir ./run-7
```

The command prints a compact JSON summary after the requested number of steps.

## Reproduction semantics

Mate candidates are intentionally **not pre-filtered by species**. If a selected partner belongs to another species, the interaction is treated as a failed cross-species mating attempt: both participants still pay the configured cooldown, energy, and fatigue costs, no offspring are produced, and the simulation increments `hybrid_attempts`.

This is a deliberate model rule used to measure unsuccessful cross-species mating attempts, not an accidental omission of a species filter.

## Run the visual simulation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python src/main.py --seed 7
```

Optional fullscreen mode:

```bash
python src/main.py --seed 7 --fullscreen
```

## Tests

```bash
pytest
```

The public tests focus on reproducibility and core invariants using small populations rather than running the full default population on every CI job.

## Scope

This is an experimental simulation platform. Terms such as "economy", "language", "ownership", or "social memory" refer to mechanisms implemented inside the model; they are not claims that the simulation reproduces human society or biological reality.

## License

Source-visible, all rights reserved. See [LICENSE](LICENSE). Third-party dependencies remain subject to their own licenses.