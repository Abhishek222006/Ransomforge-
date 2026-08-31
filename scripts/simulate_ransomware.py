from __future__ import annotations

"""Demo-safe ransomware simulator for the RansomForge hackathon backend.

This script is educational only. It does not encrypt anything, does not touch
system files, and only operates inside the local `runtime_watch/` folder so the
watchdog monitor, SQLite logger, and WebSocket dashboard can show live activity.

How it behaves:
- creates multiple fake files
- rapidly modifies them
- renames them with suspicious extensions like `.locked` and `.encrypted`
- writes fake encrypted-looking text
- creates a ransom note named `README_RESTORE_FILES.txt`

Expected backend behavior:
- watchdog detects file creations/modifications/renames
- events are stored in SQLite
- WebSocket clients receive live broadcast messages
- `/events/recent` shows the generated activity

Sample console output:
    [create] note_1.txt
    [modify] note_1.txt
    [rename] note_1.txt -> note_1.txt.locked
    [ransom] README_RESTORE_FILES.txt
    [summary] created=4 modified=8 renamed=4

Cleanup after demo:
- delete the generated files inside `runtime_watch/`
- or rerun with `--cleanup-only` to remove only simulator files
"""

import argparse
import random
import string
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WATCH_DIR = REPO_ROOT / "runtime_watch"
RANSOM_NOTE_NAME = "README_RESTORE_FILES.txt"
FAKE_EXTENSIONS = [".locked", ".encrypted"]
SIM_PREFIX = "demo_ransom_"


def resolve_watch_dir() -> Path:
    """Return the guarded demo folder and create it if needed."""
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    return WATCH_DIR


def ensure_safe_target(path: Path) -> Path:
    """Ensure every file operation stays inside runtime_watch."""
    resolved = path.resolve()
    watch_root = resolve_watch_dir().resolve()
    if watch_root not in resolved.parents and resolved != watch_root:
        raise ValueError(f"Refusing to operate outside runtime_watch: {resolved}")
    return resolved


def make_fake_payload(size: int = 256) -> str:
    """Create fake encrypted-looking content for visible dashboard churn."""
    alphabet = string.ascii_letters + string.digits + "+/="
    return "".join(random.choice(alphabet) for _ in range(size))


def create_demo_files(count: int, delay: float) -> list[Path]:
    """Create fake documents in runtime_watch to trigger watchdog creation events."""
    created: list[Path] = []
    for index in range(1, count + 1):
        file_path = ensure_safe_target(resolve_watch_dir() / f"{SIM_PREFIX}file_{index}.txt")
        file_path.write_text(f"Initial demo content for file {index}\n", encoding="utf-8")
        print(f"[create] {file_path.name}")
        created.append(file_path)
        time.sleep(delay)
    return created


def rapidly_modify_files(files: list[Path], rounds: int, delay: float) -> None:
    """Modify files several times so the dashboard shows live activity."""
    for round_index in range(1, rounds + 1):
        for file_path in files:
            file_path = ensure_safe_target(file_path)
            text = make_fake_payload(192)
            file_path.write_text(
                f"[{round_index}] suspicious file churn\n{text}\n",
                encoding="utf-8",
            )
            print(f"[modify] {file_path.name}")
            time.sleep(delay)


def rename_with_suspicious_extensions(files: list[Path], delay: float) -> list[Path]:
    """Rename files to suspicious extensions without changing any real data."""
    renamed: list[Path] = []
    for index, file_path in enumerate(files):
        extension = FAKE_EXTENSIONS[index % len(FAKE_EXTENSIONS)]
        target = ensure_safe_target(file_path.with_name(file_path.name + extension))
        file_path.rename(target)
        print(f"[rename] {file_path.name} -> {target.name}")
        renamed.append(target)
        time.sleep(delay)
    return renamed


def write_fake_encrypted_text(files: list[Path], delay: float) -> None:
    """Overwrite renamed files with fake encrypted-looking text."""
    for file_path in files:
        file_path = ensure_safe_target(file_path)
        fake_cipher = make_fake_payload(512)
        file_path.write_text(
            f"=== ENCRYPTED DEMO FILE ===\n{fake_cipher}\n=== END DEMO PAYLOAD ===\n",
            encoding="utf-8",
        )
        print(f"[cipher] {file_path.name}")
        time.sleep(delay)


def create_ransom_note(delay: float) -> Path:
    """Create a fake ransom note to drive the dashboard alerts."""
    note_path = ensure_safe_target(resolve_watch_dir() / RANSOM_NOTE_NAME)
    note_path.write_text(
        "Your files were 'encrypted' for demo purposes only.\n"
        "This is a safe hackathon simulation.\n"
        "No real encryption happened.\n"
        "Restore instructions are intentionally omitted.\n",
        encoding="utf-8",
    )
    print(f"[ransom] {note_path.name}")
    time.sleep(delay)
    return note_path


def cleanup_demo_files() -> int:
    """Remove only simulator-generated files from runtime_watch."""
    watch_dir = resolve_watch_dir()
    removed = 0
    for path in watch_dir.glob(f"{SIM_PREFIX}*"):
        if path.is_file():
            path.unlink(missing_ok=True)
            removed += 1
    ransom_note = watch_dir / RANSOM_NOTE_NAME
    if ransom_note.exists():
        ransom_note.unlink()
        removed += 1
    return removed


def run_simulation(files: int, rounds: int, delay: float) -> None:
    """Run the full safe ransomware-style demo sequence."""
    print("[demo] starting safe ransomware simulation")
    print(f"[demo] writing only inside: {resolve_watch_dir()}")

    created_files = create_demo_files(files, delay)
    rapidly_modify_files(created_files, rounds, delay)
    renamed_files = rename_with_suspicious_extensions(created_files, delay)
    write_fake_encrypted_text(renamed_files, delay)
    create_ransom_note(delay)

    print("[summary] simulation complete")
    print(f"[summary] files_created={len(created_files)}")
    print(f"[summary] files_renamed={len(renamed_files)}")
    print(f"[summary] ransom_note={RANSOM_NOTE_NAME}")
    print("[summary] cleanup tip: delete runtime_watch/demo_ransom_* and README_RESTORE_FILES.txt")


def parse_args() -> argparse.Namespace:
    """Parse safe demo parameters."""
    parser = argparse.ArgumentParser(description="Safe ransomware-style demo simulator for RansomForge")
    parser.add_argument("--files", type=int, default=4, help="Number of fake files to create")
    parser.add_argument("--rounds", type=int, default=2, help="Number of rapid modify rounds")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between actions in seconds")
    parser.add_argument("--cleanup-only", action="store_true", help="Remove simulator files and exit")
    return parser.parse_args()


def main() -> None:
    """Entry point for the safe simulation script."""
    args = parse_args()
    resolve_watch_dir()

    if args.cleanup_only:
        removed = cleanup_demo_files()
        print(f"[cleanup] removed {removed} simulator files from {WATCH_DIR}")
        return

    run_simulation(files=max(1, args.files), rounds=max(1, args.rounds), delay=max(0.0, args.delay))


if __name__ == "__main__":
    main()