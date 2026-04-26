from __future__ import annotations


def create_app():
    from .app import create_app as _create_app

    return _create_app()


def main() -> None:
    from .app import main as _main

    _main()


def start(astAnalyer=None, speedAnalyer=None, workflow=None) -> None:
    from .app import start as _start

    _start(astAnalyer=astAnalyer, speedAnalyer=speedAnalyer, workflow=workflow)


__all__ = [
    "create_app",
    "main",
    "start",
]
