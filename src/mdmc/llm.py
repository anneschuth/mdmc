"""LLM interaction module for generating source code via claude -p."""

import re
import subprocess
import sys

from mdmc.prompts import ASM_SYSTEM_PROMPT, C_SYSTEM_PROMPT, RAW_SYSTEM_PROMPT, RETRY_PROMPT_TEMPLATE


def _strip_fences(text: str) -> str:
    """Remove markdown code fences and preamble text Claude might add."""
    text = text.strip()
    # Strip ```python, ```asm, ```c, or bare ``` fences
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    # Strip preamble lines before actual code (e.g., "Here is the complete script:")
    # Look for first line that starts with import, #include, #!, ., or a comment
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "#include", "#!", ".", ";", "//", "/*",
                                "from ", "def ", "class ", "struct", "int ", "void ",
                                ".section", ".globl", ".p2align")):
            text = "\n".join(lines[i:])
            break
    return text.strip()


def _call_claude(system_prompt: str, user_message: str) -> str:
    """Call Claude via `claude -p` (pipe mode) using the user's subscription."""
    # Combine system prompt and user message into the prompt
    full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "sonnet"],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError("claude -p timed out after 600s")

    if result.returncode != 0:
        print(f"Error calling claude: {result.stderr}", file=sys.stderr)
        raise SystemExit(1)

    return result.stdout.strip()


def _get_prompt_config(mode: str) -> tuple[str, str]:
    """Return (system_prompt, language_name) for a given mode."""
    if mode == "asm":
        return ASM_SYSTEM_PROMPT, "ARM64 macOS assembly"
    elif mode == "raw":
        return RAW_SYSTEM_PROMPT, "Python Mach-O builder script"
    else:
        return C_SYSTEM_PROMPT, "C"


def generate_source(spec: str, mode: str) -> str:
    """Generate assembly, C source, or raw hex from a markdown spec."""
    system_prompt, language = _get_prompt_config(mode)

    user_message = (
        f"Translate the following specification into a working "
        f"{language} program:\n\n{spec}"
    )

    source = _call_claude(system_prompt, user_message)
    return _strip_fences(source)


def retry_with_error(
    source: str,
    error: str,
    mode: str,
    stage: str = "assemble",
) -> str:
    """Ask Claude to fix source code given an error message."""
    system_prompt, language = _get_prompt_config(mode)

    user_message = RETRY_PROMPT_TEMPLATE.format(
        language=language,
        stage=stage,
        source=source,
        error=error,
    )

    source = _call_claude(system_prompt, user_message)
    return _strip_fences(source)
