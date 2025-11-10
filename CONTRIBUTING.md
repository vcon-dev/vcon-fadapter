# Contributing to vcon-fadapter

Thank you for your interest in contributing to vcon-fadapter! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue using the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Features

Feature requests are welcome! Please open an issue using the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and include:

- A clear description of the feature
- Use case and motivation
- Any alternative solutions you've considered

### Pull Requests

1. **Fork the repository** and create a new branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Run tests and linting**
   ```bash
   # Run tests
   uv run pytest
   
   # Run linting
   uv run ruff check .
   uv run black --check .
   ```

4. **Commit your changes**
   - Write clear, descriptive commit messages
   - Reference any related issues in your commit message (e.g., "Fixes #123")

5. **Push and create a Pull Request**
   - Push your branch to your fork
   - Open a pull request against the `main` branch
   - Fill out the pull request template
   - Ensure CI checks pass

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/vcon-fadapter.git
cd vcon-fadapter

# Create a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the project in development mode
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=fax_adapter --cov-report=html

# Run specific test file
uv run pytest tests/test_config.py

# Run tests in verbose mode
uv run pytest -v
```

### Code Style

This project uses:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting

Before committing, ensure your code passes:

```bash
# Format code
uv run black .

# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .
```

### Project Structure

```
vcon-fadapter/
├── fax_adapter/          # Main package
│   ├── __init__.py
│   ├── config.py         # Configuration management
│   ├── parser.py         # Filename parsing
│   ├── builder.py        # vCon creation
│   ├── poster.py         # HTTP posting
│   ├── tracker.py        # State tracking
│   └── monitor.py        # File system monitoring
├── tests/                # Test suite
├── main.py               # Entry point
└── pyproject.toml        # Project configuration
```

## Writing Tests

- Tests should be in the `tests/` directory
- Use descriptive test names (e.g., `test_parser_extracts_sender_and_receiver`)
- Follow the existing test patterns using pytest
- Aim for good test coverage, especially for new features

## Documentation

- Update the README.md if you add new features or change behavior
- Add docstrings to new functions and classes
- Update inline comments if the code logic changes significantly

## Review Process

- All pull requests require review before merging
- Maintainers will review your PR and may request changes
- Please be responsive to feedback and update your PR accordingly
- Once approved, a maintainer will merge your PR

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the "question" label
- Check existing issues and discussions

Thank you for contributing to vcon-fadapter! 🎉

