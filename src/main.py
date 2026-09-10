import argparse

import numpy as np
import pygame

import config
from simulation import Simulation


def draw_cell(screen: pygame.Surface, cell) -> None:
    if cell.species == config.SPECIES_PLANT:
        color = (0, 255, 0)
    elif cell.species == config.SPECIES_HERBIVORE:
        color = (255, 255, 0)
    elif cell.species == config.SPECIES_CARNIVORE:
        color = (255, 0, 0)
    else:
        color = cell.get_color()

    size = config.CELL_SIZE if cell.is_adult else max(1, config.CELL_SIZE // 2)
    if cell.is_sleeping:
        color = tuple(component // 3 for component in color)
    offset = (config.CELL_SIZE - size) // 2
    rect = pygame.Rect(
        cell.x * config.CELL_SIZE + offset,
        cell.y * config.CELL_SIZE + offset,
        size,
        size,
    )
    pygame.draw.rect(screen, color, rect, width=0 if cell.sex == "XX" else 1)

    if cell.gold >= 1.0:
        pygame.draw.circle(
            screen,
            (255, 215, 0),
            (
                cell.x * config.CELL_SIZE + config.CELL_SIZE // 2,
                cell.y * config.CELL_SIZE + config.CELL_SIZE // 2,
            ),
            1,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Life-Game artificial-life simulation")
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--seed", type=int, default=None, help="Seed Python and NumPy randomness.")
    parser.add_argument("--log-dir", default="log")
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_caption("Life-Game")
    flags = pygame.FULLSCREEN if args.fullscreen else 0
    screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT), flags)
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)
    simulation = Simulation(seed=args.seed, log_dir=args.log_dir)

    running = True
    paused = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_ESCAPE:
                    running = False

        if not paused:
            simulation.step()

        screen.fill(config.COLOR_BG)
        for x in range(config.GRID_W):
            for y in range(config.GRID_H):
                food = float(simulation.env.food_grid[x, y])
                stress = float(simulation.env.stress_grid[x, y])
                if food <= 0.0 and stress <= 0.0:
                    continue
                food_type = float(simulation.env.food_type_grid[x, y])
                decay = float(simulation.env.decay_grid[x, y])
                brightness = max(0.0, 1.0 - decay * 0.7)
                food_strength = min(255, int(food * 15))
                red = min(255, int(stress * 180) + int(food_type * food_strength * brightness))
                green = int((1.0 - food_type) * food_strength * brightness)
                blue = int(food_type * food_strength * brightness)
                pygame.draw.rect(
                    screen,
                    (red, green, blue),
                    pygame.Rect(
                        x * config.CELL_SIZE,
                        y * config.CELL_SIZE,
                        config.CELL_SIZE,
                        config.CELL_SIZE,
                    ),
                )

        for cell in simulation.cells:
            if cell.species == config.SPECIES_PLANT:
                draw_cell(screen, cell)
        for cell in simulation.cells:
            if cell.species != config.SPECIES_PLANT:
                draw_cell(screen, cell)

        summary = simulation.summary()
        avg_stress = (
            float(np.mean([simulation.env.stress_grid[cell.x, cell.y] for cell in simulation.cells]))
            if simulation.cells
            else 0.0
        )
        lines = [
            f"FPS: {clock.get_fps():.1f} | Step: {simulation.step_count} | Seed: {args.seed}",
            f"Population: {summary['population']} | Human {summary['human']} | Herbivore {summary['herbivore']} | Carnivore {summary['carnivore']} | Plant {summary['plant']}",
            f"Gold: {summary['total_gold']:.1f} | Food: {summary['total_food']:.1f} | Avg stress: {avg_stress:.3f}",
        ]
        if paused:
            lines.append("PAUSED — SPACE to resume")
        for index, line in enumerate(lines):
            screen.blit(font.render(line, True, (255, 255, 255)), (10, 10 + index * 17))

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
