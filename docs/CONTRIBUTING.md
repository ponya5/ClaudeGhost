# Contributing to ClaudeGhost

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

1. Fork and clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `python tests/run_all_tests.py`

## Running Tests

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test file
python -m pytest tests/test_guardian.py -v
```

All tests must pass before submitting a PR.

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to public functions
- Keep functions focused and maintainable

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run tests: `python tests/run_all_tests.py`
4. Commit with clear messages
5. Push and create a PR

## Reporting Issues

When reporting bugs, include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs

## Feature Requests

Open an issue with:
- Clear description of the feature
- Use case and benefits
- Proposed implementation (optional)

## Questions?

Open a discussion or issue on GitHub.
