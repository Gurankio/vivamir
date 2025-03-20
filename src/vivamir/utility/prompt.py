from typing import Callable

import typer
from rich import print


def prompt_until_valid(prompt: str, validate: Callable, default: str = None):
    try:
        while True:
            value = typer.prompt(prompt, default)

            if (value := validate(value)) is not None:
                return value
    except KeyboardInterrupt:
        print('[red]Aborted.')
