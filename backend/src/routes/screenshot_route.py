from pathlib import Path

screenshot_dir = Path(__file__).resolve().parent.parent.parent / "screenshots"
screenshot_dir.mkdir(parents=True,exist_ok=True)

