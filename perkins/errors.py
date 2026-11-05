"""One base class for every error Perkins raises on purpose. run.py prints these as a
plain message and exits 2; anything else is a bug and shows a traceback."""


class PerkinsError(Exception):
    """An error meant for the user: the message says what went wrong and how to fix it."""
