from pathlib import Path
import runpy

SHARED_GENERATOR = (
    Path(__file__).resolve().parents[2]
    / "Sample-Data-Health-Content"
    / "scripts"
    / "generate_seed_data.py"
)

if not SHARED_GENERATOR.is_file():
    raise FileNotFoundError(f"Shared article generator not found: {SHARED_GENERATOR}")

runpy.run_path(str(SHARED_GENERATOR), run_name="__main__")
