"""CLI entry point for mdmc."""

import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from mdmc import __version__
from mdmc.compiler import compile_spec

console = Console()


@click.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output binary path")
@click.option(
    "--mode",
    type=click.Choice(["asm", "c", "auto"]),
    default="auto",
    help="Generation mode (default: auto)",
)
@click.option("--show-source", is_flag=True, help="Print generated source code")
@click.option("--retries", default=2, help="Max retries per mode (default: 2)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def main(
    spec: str,
    output: str | None,
    mode: str,
    retries: int,
    show_source: bool,
    verbose: bool,
) -> None:
    """MDMC - Markdown to Machine Code.

    Compile a markdown specification directly to a native executable.
    Your spec IS your source code.
    """
    console.print(
        Panel(
            f"[bold]mdmc[/bold] v{__version__} - Markdown to Machine Code",
            style="blue",
        )
    )

    spec_path = Path(spec)
    if output is None:
        output = spec_path.stem

    # Step 1: Read spec
    console.print(f"  [1/3] Reading spec ........... {spec_path}", style="bold")
    spec_text = spec_path.read_text()

    if verbose:
        console.print(f"\n[dim]--- Spec ---[/dim]")
        console.print(spec_text, highlight=False)
        console.print("[dim]--- End ---[/dim]\n")

    # Steps 2-3: Generate and build
    start = time.time()
    result = compile_spec(spec_text, output, mode=mode, retries=retries, verbose=verbose)
    elapsed = time.time() - start

    if result.success:
        console.print()
        console.print(
            f"  Output: [bold green]{output}[/bold green] "
            f"(ARM64 Mach-O, mode={result.mode_used}, "
            f"{result.attempts} attempt(s), {elapsed:.1f}s)"
        )
        if show_source:
            lang = "asm" if result.mode_used == "asm" else "c"
            console.print(f"\n[dim]--- Generated {lang} source ---[/dim]")
            console.print(result.source, highlight=False)
            console.print("[dim]--- End ---[/dim]")
    else:
        console.print()
        console.print(
            f"  [bold red]Failed[/bold red] to compile after "
            f"{result.attempts} attempt(s) ({elapsed:.1f}s)"
        )
        console.print(f"  Last error:\n{result.error}", style="red")
        raise SystemExit(1)
