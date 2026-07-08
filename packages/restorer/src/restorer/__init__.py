from .restore import restore_database
from .run import run

__all__ = ["restore_database"]


def main() -> None:
    run()
