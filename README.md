# mdmc — Markdown to Machine Code

**Your spec IS your source code.**

`mdmc` takes a markdown specification and compiles it directly into a native ARM64 macOS executable. No programming language in between — just an LLM and an assembler.

```
$ mdmc examples/fizzbuzz.md -o fizzbuzz

╭──────────────────────────────────────────────────────────╮
│ mdmc v0.1.0 - Markdown to Machine Code                   │
╰──────────────────────────────────────────────────────────╯
  [1/3] Reading spec ........... examples/fizzbuzz.md
  [2/3] Generating ARM64 assembly .. done
  [3/3] Building .......... done

  Output: fizzbuzz (ARM64 Mach-O, mode=asm, 1 attempt(s), 12.4s)

$ ./fizzbuzz
1
2
Fizz
4
Buzz
Fizz
...
FizzBuzz
...
```

## How it works

1. Reads a markdown spec file
2. Sends it to Claude via `claude -p` with a carefully crafted system prompt containing ARM64 macOS assembly reference material
3. Receives raw ARM64 assembly back
4. Assembles with `as` and links with `ld` to produce a native Mach-O executable

If assembly fails, it feeds the error back to Claude for self-correction (up to N retries). In `auto` mode, it falls back to C if assembly can't be made to work.

## Installation

Requires [uv](https://docs.astral.sh/uv/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`claude` CLI must be on your PATH).

```bash
git clone https://github.com/anneschuth/mdmc.git
cd mdmc
uv sync
```

## Usage

```bash
# Basic usage — produces a native binary
uv run mdmc examples/hello.md -o hello
./hello
# Hello, World!

# See the generated assembly
uv run mdmc examples/fibonacci.md -o fib --show-source

# Force C mode (more reliable for complex programs)
uv run mdmc examples/primes.md -o primes --mode c

# Verbose output with all intermediate steps
uv run mdmc examples/sort.md -o sort -v

# Directly produce byte code, skip assembly
uv run mdmc examples/hello.md -o hello_raw --mode raw
```

### Options

| Flag | Description |
|------|-------------|
| `-o, --output` | Output binary path (default: spec filename) |
| `--mode raw\|asm\|c\|auto` | Generation mode (default: `auto`) |
| `--show-source` | Print the generated assembly/C source |
| `--retries N` | Max retries per mode with error feedback (default: 2) |
| `-v, --verbose` | Show spec, generated source, and errors |

## Examples

| Spec | Description | Mode | Self-corrections |
|------|-------------|------|-----------------|
| [hello.md](examples/hello.md) | Hello, World! | asm | 0 |
| [fizzbuzz.md](examples/fizzbuzz.md) | FizzBuzz 1-100 | asm | 1 |
| [fibonacci.md](examples/fibonacci.md) | First 20 Fibonacci numbers | asm | 2 |
| [diamond.md](examples/diamond.md) | Asterisk diamond pattern | asm | 1 |
| [sort.md](examples/sort.md) | Bubble sort with before/after | asm | 2 |
| [rot13.md](examples/rot13.md) | ROT13 cipher (stdin → stdout) | asm | 1 |
| [calculator.md](examples/calculator.md) | `12 + 34` → `46` (stdin parser) | asm | 1 |
| [primes.md](examples/primes.md) | Sieve of Eratosthenes to 200 | C fallback | 0 |
| [maze.md](examples/maze.md) | 15×15 maze generator | C | 1 |

7 out of 9 examples compile to **pure ARM64 assembly** from nothing but a markdown description.

## The philosophy

This started as a thought experiment: can LLMs bypass traditional programming and compile specs directly to machine code? Turns out — mostly yes.

The LLM acts as the compiler frontend and middle-end: it reads natural language, understands the intent, and produces correct program logic as ARM64 assembly. The assembler (`as`) is just the trivial last step — a 1:1 mapping of mnemonics to opcodes.

Every traditional compiler has intermediate representations (`C → AST → GIMPLE → RTL → asm → machine code`). Here, assembly is our IR. The hard part — going from human intent to correct logic — is what the LLM does.

**Is there source code in between?** Yes, assembly. But the interesting question isn't whether there's an intermediate representation (there always is). It's whether a system can reliably go from natural-language spec to working executable. This one can.

## Requirements

- macOS on Apple Silicon (ARM64)
- [uv](https://docs.astral.sh/uv/)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI (`claude` on PATH, with active subscription)
- Xcode Command Line Tools (`xcode-select --install`)

## License

MIT
