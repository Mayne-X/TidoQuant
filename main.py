"""Main Entrypoint — starts the bot loop and the dashboard API server."""
from src.api_server import run_api_server
from src.database import migrate
from src.logger import configure_logging
from src.main_loop import run_loop

if __name__ == "__main__":
    configure_logging()
    migrate()
    run_api_server(port=4900)
    try:
        run_loop()
    except KeyboardInterrupt:
        print("Bot stopped.")
