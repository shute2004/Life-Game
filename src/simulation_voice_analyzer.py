import config
from cell import Cell


class SimulationVoiceAnalyzer:
    @staticmethod
    def determine_exteriors_state(cell: Cell, env) -> str:
        if cell.energy < 15.0:
            return "starving"
        if float(env.stress_grid[cell.x, cell.y]) > 0.5:
            return "danger"
        if cell.is_adult and cell.energy >= cell.genes["repro_threshold"]:
            return "mating_ready"
        return "normal"

    @classmethod
    def check_and_log_conversations(
        cls,
        step_count: int,
        speaker: Cell,
        pos_to_cell: dict,
        voice_log_paths: dict,
        trackers: dict,
        env,
    ) -> None:
        if speaker.is_sleeping or speaker.is_dead or not speaker.voice:
            return

        voice_key = f"voice:{speaker.voice}"
        actual_state = cls.determine_exteriors_state(speaker, env)
        matched: list[str] = []

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = speaker.x + dx, speaker.y + dy
                if not (0 <= nx < config.GRID_W and 0 <= ny < config.GRID_H):
                    continue
                listener = pos_to_cell.get((nx, ny))
                if listener is None or listener == speaker or listener.is_dead or listener.is_sleeping:
                    continue
                predicted = listener.infer_association(voice_key)
                if predicted:
                    strength = listener.association_memory[voice_key].get(predicted, 0.0)
                    matched.append(
                        f"{listener.id}:{listener.species}[{predicted.split(':')[-1]}:{strength:.1f}]"
                    )

        if matched and speaker.species in voice_log_paths:
            trackers["conversation_count"] += 1
            with open(voice_log_paths[speaker.species], "a", encoding="utf-8") as file:
                file.write(
                    f"{step_count},{speaker.id},{speaker.x},{speaker.y},"
                    f"{speaker.voice},{actual_state},{'|'.join(matched)}\n"
                )
