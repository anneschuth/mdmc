"""Orchestration: spec -> LLM -> assemble -> binary."""

from dataclasses import dataclass

from rich.console import Console

from mdmc.assembler import BuildResult, assemble_and_link, compile_c, write_raw_binary
from mdmc.llm import generate_source, retry_with_error

console = Console()


@dataclass
class CompileResult:
    success: bool
    mode_used: str
    source: str
    error: str = ""
    attempts: int = 0


def _try_build(
    spec: str,
    mode: str,
    output: str,
    retries: int,
    verbose: bool,
) -> CompileResult:
    """Try to generate and build in a given mode with retries."""
    language = {"asm": "ARM64 assembly", "c": "C", "raw": "raw Mach-O hex"}[mode]

    console.print(f"  [2/3] Generating {language}", end=" ", style="bold")
    try:
        source = generate_source(spec, mode)
    except TimeoutError as e:
        console.print(f".. timeout", style="red")
        return CompileResult(
            success=False,
            mode_used=mode,
            source="",
            error=str(e),
            attempts=0,
        )
    console.print(".. done", style="green")

    if verbose:
        console.print(f"\n[dim]--- Generated {language} ---[/dim]")
        console.print(source, highlight=False)
        console.print("[dim]--- End ---[/dim]\n")

    for attempt in range(1 + retries):
        console.print("  [3/3] Building", end=" ", style="bold")

        if mode == "asm":
            result: BuildResult = assemble_and_link(source, output)
        elif mode == "raw":
            result = write_raw_binary(source, output)
        else:
            result = compile_c(source, output)

        if result.success:
            console.print(".......... done", style="green")
            return CompileResult(
                success=True,
                mode_used=mode,
                source=source,
                attempts=attempt + 1,
            )

        console.print(f".......... failed ({result.stage})", style="red")
        if verbose:
            console.print(f"[red]{result.error}[/red]")

        if attempt < retries:
            console.print(
                f"  [*] Retry {attempt + 1}/{retries}: feeding error back to LLM",
                style="yellow",
            )
            try:
                source = retry_with_error(
                    source, result.error, mode, stage=result.stage
                )
            except TimeoutError:
                console.print("  [*] Retry timed out", style="red")
                break
            if verbose:
                console.print(f"\n[dim]--- Corrected {language} ---[/dim]")
                console.print(source, highlight=False)
                console.print("[dim]--- End ---[/dim]\n")

    return CompileResult(
        success=False,
        mode_used=mode,
        source=source,
        error=result.error,
        attempts=1 + retries,
    )


def compile_spec(
    spec: str,
    output: str,
    mode: str = "auto",
    retries: int = 2,
    verbose: bool = False,
) -> CompileResult:
    """Compile a markdown spec to a binary executable.

    Modes:
        asm  - ARM64 assembly only
        c    - C only
        auto - try asm first, fall back to C
    """
    if mode == "asm":
        return _try_build(spec, "asm", output, retries, verbose)
    elif mode == "c":
        return _try_build(spec, "c", output, retries, verbose)
    elif mode == "raw":
        return _try_build(spec, "raw", output, retries, verbose)
    else:
        # Auto mode: try asm, fall back to C
        result = _try_build(spec, "asm", output, retries, verbose)
        if result.success:
            return result

        console.print(
            "\n  [!] Assembly failed, falling back to C...\n", style="yellow"
        )
        return _try_build(spec, "c", output, retries, verbose)
