"""Assembler and linker module for producing executables."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BuildResult:
    success: bool
    error: str = ""
    stage: str = ""  # "assemble", "link", or "compile"


def _get_sdk_path() -> str:
    """Get the macOS SDK path via xcrun."""
    result = subprocess.run(
        ["xcrun", "--show-sdk-path"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def assemble_and_link(source: str, output: str) -> BuildResult:
    """Assemble ARM64 source and link into a Mach-O executable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "program.s"
        obj_path = Path(tmpdir) / "program.o"
        src_path.write_text(source)

        # Assemble
        result = subprocess.run(
            ["as", "-arch", "arm64", "-o", str(obj_path), str(src_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return BuildResult(
                success=False,
                error=result.stderr,
                stage="assemble",
            )

        # Link
        sdk_path = _get_sdk_path()
        result = subprocess.run(
            [
                "ld",
                "-o",
                output,
                str(obj_path),
                "-lSystem",
                "-syslibroot",
                sdk_path,
                "-e",
                "_main",
                "-arch",
                "arm64",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return BuildResult(
                success=False,
                error=result.stderr,
                stage="link",
            )

    return BuildResult(success=True)


def compile_c(source: str, output: str) -> BuildResult:
    """Compile C source into an executable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "program.c"
        src_path.write_text(source)

        result = subprocess.run(
            ["clang", "-o", output, str(src_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return BuildResult(
                success=False,
                error=result.stderr,
                stage="compile",
            )

    return BuildResult(success=True)
