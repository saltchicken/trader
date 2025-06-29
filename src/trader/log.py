from loguru import logger
import os
import sys

# Path to the current script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
script_name = os.path.splitext(os.path.basename(script_path))[0]

# Create log file path: same directory, same name, .log extension
log_path = os.path.join(script_dir, f"{script_name}.log")

# Configure loguru
logger.remove()  # Remove default stderr handler
logger.add(
    log_path,
    rotation="1 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DDTHH:mm:ssZ!UTC} | {level} | {message}",
)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Let KeyboardInterrupt pass silently
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.opt(exception=(exc_type, exc_value, exc_traceback)).error(
        "Uncaught exception"
    )


sys.excepthook = handle_exception
