import argparse
import json

from simulation import Simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Life-Game without the Pygame renderer.")
    parser.add_argument("--seed", type=int, default=0, help="Seed for Python and NumPy randomness.")
    parser.add_argument("--steps", type=int, default=100, help="Number of simulation steps to run.")
    parser.add_argument("--log-dir", default="log", help="Directory for audit and voice logs.")
    args = parser.parse_args()

    if args.steps < 0:
        parser.error("--steps must be non-negative")

    simulation = Simulation(seed=args.seed, log_dir=args.log_dir)
    for _ in range(args.steps):
        simulation.step()

    if simulation.step_count % 10 != 0:
        simulation.log_stats()

    print(json.dumps(simulation.summary(), sort_keys=True))


if __name__ == "__main__":
    main()
