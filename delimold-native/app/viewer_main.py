"""Read-only DELIMOLD viewer entry point for SALAK."""
from app.main import main


if __name__ == "__main__":
    raise SystemExit(main(force_viewer=True))
