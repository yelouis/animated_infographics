"""CLI entry point for Animated Infographics."""

import sys

import typer

from animated_infographics.doctor import run_doctor

app = typer.Typer(no_args_is_help=True, help="Animated Infographics CLI")


@app.callback()
def main() -> None:
    """Animated Infographics command-line tool."""


@app.command("doctor")
def doctor() -> None:
    """Run environment, model, tool, and asset checks."""
    code = run_doctor()
    if code != 0:
        sys.exit(code)


if __name__ == "__main__":
    app()
