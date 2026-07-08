from .models import CompanyInfo
from .run import run

__all__ = ["CompanyInfo"]


def main() -> None:
    print("Hello from reporting!")
    run()
