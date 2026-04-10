from pathlib import Path


def main() -> int:
    try:
        from src.ui.pyqt.app import run_app
    except ImportError as exc:
        raise SystemExit(
            "PyQt6 is not installed. Install it with 'pip install PyQt6' and run again."
        ) from exc

    return run_app(Path(__file__).parent)


if __name__ == "__main__":
    raise SystemExit(main())
