import sys
from logbook import StreamHandler
from logbook.compat import redirect_logging


def init_logging():
    StreamHandler(sys.stdout).push_application()
    redirect_logging()
