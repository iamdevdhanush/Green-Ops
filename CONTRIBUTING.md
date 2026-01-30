# Contributing to GreenOps

Thank you for your interest in contributing to GreenOps! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and professional. We're all here to make IT infrastructure more sustainable.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (OS, Python version, etc.)
   - Logs if applicable

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with:
   - Clear description of the feature
   - Use case and benefits
   - Possible implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Update documentation
7. Commit with clear messages
8. Push to your fork
9. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/greenops.git
cd greenops

# Server setup
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Agent setup
cd ../agent
pip install -r requirements.txt
```

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and small
- Comment complex logic

### Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=greenops tests/
```

### Documentation

- Update README.md for user-facing changes
- Update API.md for API changes
- Add inline comments for complex code
- Update CHANGELOG.md

## Project Structure

```
greenops/
├── server/          # Flask server
│   ├── app.py      # Main application
│   ├── templates/  # HTML templates
│   └── ...
├── agent/          # System agent
│   ├── agent.py    # Main agent
│   └── ...
├── docs/           # Documentation
└── tests/          # Test suite
```

## Areas Needing Help

- macOS improvements
- Additional ML models
- Cloud provider integrations
- Mobile apps
- Translations
- Documentation
- Testing

## Questions?

Open an issue or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
