"""LLM interaction module for generating source code via claude -p."""

import re
import subprocess
import sys

from mdmc.prompts import ASM_SYSTEM_PROMPT, C_SYSTEM_PROMPT, RETRY_PROMPT_TEMPLATE


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if Claude adds them despite instructions."""
    text = re.sub(r"^```\w*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


def _call_claude(system_prompt: str, user_message: str) -> str:
    """Call Claude via `claude -p` (pipe mode) using the user's subscription."""
    # Combine system prompt and user message into the prompt
    full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    try:
        result = subprocess.run(
            ["claude", "-p"],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError("claude -p timed out after 300s")

    if result.returncode != 0:
        print(f"Error calling claude: {result.stderr}", file=sys.stderr)
        raise SystemExit(1)

    return result.stdout.strip()


def generate_source(spec: str, mode: str) -> str:
    """Generate assembly or C source from a markdown spec."""
    system_prompt = ASM_SYSTEM_PROMPT if mode == "asm" else C_SYSTEM_PROMPT
    language = "ARM64 macOS assembly" if mode == "asm" else "C"

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
    system_prompt = ASM_SYSTEM_PROMPT if mode == "asm" else C_SYSTEM_PROMPT
    language = "ARM64 macOS assembly" if mode == "asm" else "C"

    user_message = RETRY_PROMPT_TEMPLATE.format(
        language=language,
        stage=stage,
        source=source,
        error=error,
    )

    source = _call_claude(system_prompt, user_message)
    return _strip_fences(source)
