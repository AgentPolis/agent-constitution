# Contributing to Agent Constitution

Thanks for your interest in contributing. Here's how to get started.

## Setup

```bash
git clone <your-fork-or-origin-url>
cd agent-constitution
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Development Workflow

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Run tests: `pytest --tb=short -v`
4. Run linter: `ruff check . --exclude .venv`
5. Optionally verify packaging: `python -m build`
6. Open a PR

## Code Style

- Python 3.11+
- Ruff for linting (config in `pyproject.toml`)
- Type hints on public APIs
- Tests for all new functionality (use `MockAdapter`, never require API keys)

## Architecture Rules

- **Generator/Validator separation**: LLM output is generated, then validated by a separate function. Never trust raw LLM output.
- **Strict-by-default debate validation**: malformed challenger, defender, or judge output should fail closed unless a caller explicitly opts into fallback mode.
- **Constitution as markdown**: Rules live in `.md` files, not Python strings.
- **Cost guard pre-check**: Budget limits checked before recording, not after.

## What We Need Help With

- New LLM adapters (OpenAI, Google, Groq, Together)
- More SOUL.md examples for different domains
- Better MockAdapter responses
- Documentation improvements
- Translations

## Tests

All tests must pass with `MockAdapter` and zero API keys:

```bash
pytest --tb=short -v
```

206 tests currently. Please add tests for any new functionality.

## Pull Request Guidelines

- Keep PRs focused. One feature or fix per PR.
- Include tests.
- Update README if you add user-facing features.
- Reference any related issues.

## License

By contributing, you agree to the project's [Contributor License Agreement (CLA)](CLA.md). This lets us maintain the project's licensing flexibility while keeping it open source under Apache-2.0.
