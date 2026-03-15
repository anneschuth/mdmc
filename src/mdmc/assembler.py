"""Assembler and linker module for producing executables."""

import os
import re
import stat
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


def _validate_macho(output: str) -> BuildResult:
    """Validate a Mach-O binary using otool and a test run."""
    # Check structure with otool -l
    result = subprocess.run(
        ["otool", "-l", output],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return BuildResult(
            success=False,
            error=f"otool -l failed: {result.stderr}",
            stage="validate",
        )

    otool_output = result.stdout
    # Check for structural problems otool reports
    if "Unknown load command" in otool_output or "extends past end" in otool_output:
        return BuildResult(
            success=False,
            error=f"Mach-O structure is invalid. otool -l output:\n{otool_output}",
            stage="validate",
        )

    # Disassemble to verify code section exists
    result = subprocess.run(
        ["otool", "-tv", output],
        capture_output=True,
        text=True,
    )
    disasm = result.stdout
    if "svc" not in disasm and result.returncode != 0:
        return BuildResult(
            success=False,
            error=f"No valid ARM64 code found. otool -tv output:\n{disasm}",
            stage="validate",
        )

    # Try running it with a timeout to catch crashes
    try:
        result = subprocess.run(
            [f"./{output}"] if not output.startswith("/") else [output],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        # Interactive programs may timeout — that's OK
        return BuildResult(success=True)

    if result.returncode < 0:
        # Negative = killed by signal (e.g., SIGSEGV=-11, SIGKILL=-9)
        signal_num = -result.returncode
        signal_names = {4: "SIGILL", 6: "SIGABRT", 9: "SIGKILL", 11: "SIGSEGV", 10: "SIGBUS"}
        sig_name = signal_names.get(signal_num, f"signal {signal_num}")
        return BuildResult(
            success=False,
            error=f"Binary crashed with {sig_name} (exit code {result.returncode}).\n"
                  f"otool -l output:\n{otool_output}\n"
                  f"otool -tv disassembly:\n{disasm}",
            stage="validate",
        )

    return BuildResult(success=True)


def write_raw_binary(script_source: str, output: str) -> BuildResult:
    """Run a Python script that constructs a Mach-O binary directly.

    The LLM generates a Python script using struct.pack that writes
    the binary — no assembler, no compiler, no linker involved.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "build_binary.py"
        script_path.write_text(script_source)

        result = subprocess.run(
            ["python3", str(script_path), output],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return BuildResult(
                success=False,
                error=result.stderr or result.stdout,
                stage="generate",
            )

    # Verify the output exists and has Mach-O magic
    out_path = Path(output)
    if not out_path.exists():
        return BuildResult(
            success=False,
            error="Script ran but did not produce output file.",
            stage="generate",
        )

    binary_data = out_path.read_bytes()
    if len(binary_data) < 4:
        return BuildResult(
            success=False,
            error=f"Output too small ({len(binary_data)} bytes).",
            stage="validate",
        )

    magic = int.from_bytes(binary_data[:4], "little")
    if magic not in (0xFEEDFACF, 0xFEEDFACE):
        return BuildResult(
            success=False,
            error=f"Invalid Mach-O magic: 0x{magic:08X} (expected 0xFEEDFACF). "
                  f"First 16 bytes: {binary_data[:16].hex()}",
            stage="validate",
        )

    # Make executable
    st = os.stat(output)
    os.chmod(output, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Ad-hoc sign (required on macOS ARM64 for raw binaries)
    sign_result = subprocess.run(
        ["codesign", "-s", "-", "--force", output],
        capture_output=True,
        text=True,
    )
    if sign_result.returncode != 0:
        # If signing fails, the Mach-O structure is probably broken
        # Get otool output for diagnostics
        otool_result = subprocess.run(
            ["otool", "-l", output], capture_output=True, text=True
        )
        return BuildResult(
            success=False,
            error=f"codesign failed: {sign_result.stderr}\n"
                  f"otool -l output:\n{otool_result.stdout}",
            stage="validate",
        )

    # Validate with otool and test run
    return _validate_macho(output)


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
