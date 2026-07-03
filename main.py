"""Main Entrypoint."""
from src.logger import configure_logging
from src.main_loop import run_loop

if __name__ == "__main__":
    configure_logging()
    try:
        run_loop()
    except KeyboardInterrupt:
        print("Bot stopped.")
