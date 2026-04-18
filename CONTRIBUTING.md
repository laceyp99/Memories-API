# Contributing to Memories API

First off, thank you for considering contributing to Memories API! It's people like you that make this project such a great tool.

To help you get started, please follow these guidelines.

## How Can I Contribute?

### Reporting Bugs
Before creating bug reports, please check the [existing issues](https://github.com/laceyp99/Memories-API/issues) to see if the problem has already been reported. When creating a bug report, please include:
* A clear and descriptive title.
* Steps to reproduce the bug.
* Expected vs. actual behavior.
* Your environment details (OS, version, etc.).

### Suggesting Enhancements
Enhancement suggestions are tracked as [GitHub issues](https://github.com/laceyp99/Memories-API/issues).
* Use a clear and descriptive title.
* Provide a step-by-step description of the suggested enhancement.
* Explain why this enhancement would be useful to most users.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code follows the [Project Style Guide](#style-guides).
5. Read the [template](.github/pull_request_template.md) and submit a pull request!

## Development Setup
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Style Guides
### Git Commit Messages
- Make each commit a coherent unit of change

### Git Branch Naming
- Use the template: `<type>/<short-description>`
- Use action prefixes for the type: `feat/*`, `fix/*`, `refactor/*`, or `chore/*`

## Additional Resources
* [Project Documentation](docs/)
