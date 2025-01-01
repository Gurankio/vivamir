from typing import Optional, Callable
from rich import print

import typer


def prompt_until_valid[T](prompt: str, validate: Callable[[str], Optional[T]], default: str = None) -> T:
    try:
        while True:
            value = typer.prompt(prompt, default)

            if (value := validate(value)) is not None:
                return value
    except KeyboardInterrupt:
        print('[red]Aborted.')
