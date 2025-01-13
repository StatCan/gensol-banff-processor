import logging
import sys
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path

from banff import logging as blg

from banffprocessor.nls import _

# list of 0 or more log handler(s) which Banff Procedure C code output should be written to
_c_handlers: list[logging.FileHandler] = []

def get_file_handler(filename: str, trace_level: int = logging.DEBUG) -> RotatingFileHandler:
    """Get a RotatingFileHandler object configured for the banffprocessor project.

    The filename will be appended with the current datetime in order to
    allow a new file to be created every run.

    :param filename: The base name to use for the new log file, defaults to LOG_FILE
    :type filename: str, optional
    :param trace_level: The logging level to set the file handler for, defaults to logging.DEBUG
    :type trace_level: int, optional
    :return: A RotatingFileHandler object configured for the banffprocessor project.
    :rtype: RotatingFileHandler
    """
    # Use a rotatingfilehandler to roll the log over every job run
    # Old log file will be appended with a number every new run, where smaller number = more recents
    log_filename = Path(f"{filename}.log")
    should_rollover = log_filename.is_file()
    file_handler = RotatingFileHandler(log_filename, backupCount=5)
    if should_rollover:
        file_handler.doRollover()

    # use custom formatter
    file_handler.setFormatter(blg.SpecialFormatter())
    file_handler.setLevel(trace_level)

    return file_handler

def add_file_handlers(log_directory: str | Path = ".//",
                      trace_level: int | None = logging.INFO,
                      filename: str = "banffprocessor") -> None:
    """Add a file handler to the top-level logger, depending on `trace_level`.

    If `trace_level` is greater than INFO, no file handlers are added. If exactly equal
    to INFO, an INFO-level handler is created. If less than INFO, a DEBUG-level
    handler is created.
    If there are already any existing FileHandlers (or subclass of FileHandler, such as
    RotatingFileHandler) attached, they are removed prior to adding any new ones.
    Also updates `_c_handlers` to list all current handlers which should receive C output.
    Filename for logs is: banffprocessor.log.

    :param log_directory: The directory where new log files should be created, defaults to ".//"
    :type log_directory: str | Path, optional
    :param trace_level: The logging level to set the file handler for, defaults to logging.DEBUG
    :type trace_level: int, optional
    :param filename: The base filename to use for the filehandlers, defaults to banffprocessor
    :type filename: str, optional
    """
    logger = blg.get_top_logger()

    global _c_handlers  # refer to module-level variable

    handlers = []
    for h in logger.handlers:
        if(isinstance(h, logging.FileHandler)):
            # If log_directory is a strict subfolder of the current filehandler,
            # return and continue to log to the original log file. This means the
            # new log_directory is coming from a process block and we want to only
            # log to the original, base log file.
            # Otherwise we continue as normal: remove existing and add new. This is
            # more likely to happen when running pytests, as the logger is not
            # destroyed and recreated with each test, a new filehandler is simply
            # recreated pointing to the new location
            if(Path(log_directory).is_relative_to(Path(h.baseFilename).parent)):
                return
        else:
            handlers.append(h)

    # Remove all handlers that are instances of FileHandler
    logger.handlers = handlers
    # also clear _c_handlers
    _c_handlers = []

    # If no trace_level is set, just remove existing handlers above and don't add any more
    if(trace_level is None):
        # With no log files we want to filter pandas FutureWarning's from user's stderr/out
        # Check sys.warnoptions in case an alternative filter option was defined
        # by the interpreter
        # Other warning types are not disabled and will display in wherever stderr
        # is pointing
        if not sys.warnoptions:
            warnings.simplefilter(action="ignore", category=FutureWarning)
        return

    # Ensure warnings are re-enabled in case they were previously disabled by this method
    warnings.simplefilter(action="default", category=FutureWarning)

    if(trace_level <= logging.INFO):
        handler = get_file_handler(trace_level=trace_level,
                                   filename=str(Path(log_directory).joinpath(filename)))

        logger.addHandler(handler)
        _c_handlers.append(handler)  # C code output should be written here

        # Redirect warnings from stdout/err to the filehandler
        # Check warnoptions first in case an alternative config has been set
        if(not sys.warnoptions):
            logging.captureWarnings(True)
            warning_log = logging.getLogger("py.warnings")
            warning_log.addHandler(handler)

    print(_("Logging to {}").format(handler.baseFilename)) # noqa: T201

def setup_processor_logger() -> logging.Logger:
    """Setup the Processor logger by initializing and configuring console and file output.

    :return: _description_
    :rtype: logging.Logger
    """
    top_logger = blg.get_top_logger()

    # The only thing we want printed to console are ERRORs and single-line proc headers
    console_handler = [h for h in top_logger.handlers if isinstance(h, logging.StreamHandler)][0]
    console_handler.setLevel(blg.log_levels.ERROR)

    return blg.init_proc_level(logger_name="processor", trace_level=blg.log_levels.DEBUG)

def get_processor_child_logger(name: str) -> logging.Logger:
    """Get the proc-level logger under `name`."""
    return blg.init_proc_level(logger_name=name,
                               parent_name="banff.processor",
                               trace_level=blg.log_levels.DEBUG)

def get_child_stream_logger(name: str) -> logging.Logger:
    """Get a proc-level logger under `name` with no handlers but a single console debug stream."""
    new_log = blg.init_proc_level(logger_name=name,
                                  parent_name="banff.processor",
                                  trace_level=blg.log_levels.DEBUG)

    # Get the stream used in the top-level streamhandler
    top_logger = blg.get_top_logger()
    console_handler = [h for h in top_logger.handlers if isinstance(h, logging.StreamHandler)][0]

    # We want the console handler here to be as permissive as possible
    new_handler = logging.StreamHandler(console_handler.stream)
    new_handler.setLevel(blg.log_levels.DEBUG)
    new_log.handlers = [new_handler]
    # Turn propagation off so the handlers on the parent don't print to file anyways
    new_log.propagate = 0

    return new_log

def get_c_handlers() -> list[logging.FileHandler]:
    """Get list of logging handler(s) which C code output should be written to."""
    global _c_handlers
    return _c_handlers
