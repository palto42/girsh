# Copilot Instructions for girsh

## Project Overview

**girsh** (Git Install Released Software Helper) is a Python tool for downloading and installing released binaries from GitHub repositories on Linux systems. It reads YAML configuration files to define GitHub release pages, binary package patterns, and extraction rules, then handles downloads, extraction, renaming, and installation to appropriate binary folders.

### Key Features

- Download releases from GitHub repositories based on regex patterns
- Extract archives securely (.tar.gz/.tgz, .zip, .tar.bz2/.bz2)
- Support for custom release sources via configurable APIs
- Optional renaming with filter and pattern rules
- Automatic installation to user or system binary folders
- Re-installation support with `--reinstall` option
- Uninstallation with `--uninstall` and `--uninstall-all` options
- Installation tracking and version caching
- Pre/post update/uninstall command execution
- Dry-run mode for testing operations

---

## Development Workflow

### Environment Setup

This project uses **UV** for Python package management. All Python commands must be run through UV:

```bash
# Initial setup
uv sync
uv run pre-commit install

# Run any Python command
uv run python <script.py>
uv run pytest
uv run mkdocs serve
```

### Quick Commands (Makefile)

Use the Makefile for common development tasks:

```bash
make install      # Set up virtual environment and pre-commit hooks
make check        # Run all code quality checks
make test         # Run tests with coverage
make build        # Build wheel distribution
make docs         # Build and serve documentation
make docs-test    # Test documentation build
make help         # Show all available commands
```

---

## Code Quality Tools

### 1. **Ruff** - Linting and Formatting

Configuration in `pyproject.toml`:

- **Target Python**: 3.10+
- **Line length**: 120 characters
- **Auto-fix enabled**: yes

#### Key Rules for Ruff

- **flake8-2020**: Version detection (YTT)
- **flake8-bandit**: Security (S)
- **flake8-bugbear**: Bug detection (B)
- **flake8-builtins**: Builtin shadowing (A)
- **flake8-comprehensions**: Comprehension optimization (C4)
- **flake8-debugger**: Debugger detection (T10)
- **flake8-simplify**: Code simplification (SIM)
- **isort**: Import sorting (I)
- **pycodestyle**: Style guide (E, W)
- **pyflakes**: Logic errors (F)
- **pygrep-hooks**: Pattern detection (PGH)
- **pyupgrade**: Syntax modernization (UP)
- **ruff**: Ruff-specific rules (RUF)
- **tryceratops**: Exception handling (TRY)

#### Ignored Rules for Ruff

- E501: Line too long (handled by format)
- E731: Lambda assignment

#### Ruff usage

```bash
# Run via Makefile (through pre-commit)
make check

# Or manually with UV
uv run ruff check src/
uv run ruff format src/
uv run ruff check --fix src/
```

### 2. **Ty** - Static Type Checking

Configuration in `pyproject.toml`:

- **Python executable**: ./.venv
- **Target version**: Python 3.12

#### Ty usage

```bash
make check  # Includes ty check

# Or manually
uv run ty check
```

### 3. **Pre-commit Hooks**

Automatically runs on every commit:

- Ruff linting and formatting
- Type checking with Ty
- Dependency checking with Deptry

Install with:

```bash
uv run pre-commit install
```

---

## Testing

### Test Configuration

- **Test framework**: pytest
- **Coverage tracking**: pytest-cov
- **Test location**: `tests/`
- **Coverage threshold**: Configured in `pyproject.toml`

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
uv run python -m pytest tests/test_girsh.py -v

# Run core module tests
uv run python -m pytest tests/core/ -v

# Generate HTML coverage report
uv run python -m pytest --cov --cov-report=html
open htmlcov/index.html
```

### Writing Tests

- Place tests in `tests/` directory mirroring source structure
- Use pytest fixtures from `conftest.py` if available
- Mock external HTTP requests and file system operations
- Ensure asserts are used (permitted in test files)
- **Test code must pass Ruff and Ty validation**: All test code must comply with the project's linting and type checking rules
  - Run `make check` to validate test code against Ruff rules
  - Run `uv run ty check` to verify type hints in tests
  - Tests follow the same code quality standards as source code
- **Inline ignore comments are acceptable** in tests when dealing with complex testing scenarios:
  - Use `# noqa:` for Ruff and `# ty: ignore` for Ty when necessary
  - Acceptable cases: mocked functions/classes causing type errors, test-specific patterns
  - Always prefer fixing the issue if practical; use inline comments only when the fix is overly complex for testing purposes
  - Include a comment explaining why the ignore is needed

---

## Project Structure

```text
girsh/
├── src/girsh/
│   ├── __init__.py
│   ├── girsh.py              # Main CLI entry point
│   └── core/                 # Core functionality
│       ├── config.py         # Configuration handling and CLI args
│       ├── files.py          # File operations (download, extract, copy)
│       ├── installed.py      # Installation tracking
│       ├── repos.py          # Repository processing logic
│       └── utils.py          # Utility functions
├── tests/
│   ├── test_girsh.py         # Main CLI tests
│   └── core/                 # Core module tests
│       ├── test_config.py
│       ├── test_installed.py
│       ├── test_utils.py
│       ├── files/
│       └── repos/
├── docs/                     # MkDocs documentation
├── Makefile                  # Development commands
├── pyproject.toml           # Project configuration
├── .pre-commit-config.yaml  # Pre-commit hooks
└── .github/
    └── copilot-instructions.md  # This file
```

---

## Main Script Functions

### `main()` - CLI Entry Point

Main entry point that orchestrates all operations.

- **Parameters**: Command-line arguments
- **Returns**: int (exit code)
- **Operations**: Config loading, privilege elevation, repository processing, installation tracking

### `process_repositories()` - Core Processing

Processes all configured repositories for installation/update.

- **Parameters**: repositories dict, general config, installed dict, reinstall list, dry_run bool
- **Returns**: tuple(installed dict, summary dict)
- **Operations**: Downloads releases, extracts binaries, installs to system/user paths

### `uninstall()` - Package Removal

Uninstalls specified repositories or all installed packages.

- **Parameters**: repositories list, installed dict, dry_run bool
- **Returns**: dict (uninstall summary)
- **Operations**: Removes binaries, cleans up package directories, executes pre/post commands

### `download_github_release()` - Download Logic

Downloads release assets from GitHub API.

- **Parameters**: repo str, version str, pattern str, download_dir Path
- **Returns**: Path (downloaded file path)
- **Error handling**: API errors, network issues, pattern matching failures

### `extract_package()` - Archive Extraction

Extracts downloaded archives and finds binary files.

- **Parameters**: archive_path Path, extract_to Path, binary_pattern str
- **Returns**: Path (extracted binary path)
- **Supports**: .tar.gz, .zip, .tar.bz2 formats

### `copy_to_bin()` - Binary Installation

Copies binaries to appropriate system/user binary directories.

- **Parameters**: source Path, binary_name str, bin_base_folder Path
- **Returns**: bool (success/failure)
- **Logic**: Uses /usr/local/bin for root, ~/.local/bin for users

---

## Dependencies

### Core Dependencies

- `loguru>=0.7.3` - Structured logging with colors
- `psutil>=7.0.0` - System process utilities
- `pyyaml>=6.0.2` - YAML configuration parsing
- `requests>=2.32.3` - HTTP client for GitHub API

### Development Dependencies

- `pytest>=7.2.0` - Testing framework
- `pre-commit>=2.20.0` - Git hooks management
- `tox-uv>=1.11.3` - Testing across Python versions
- `deptry>=0.23.0` - Dependency analysis
- `pytest-cov>=4.0.0` - Coverage reporting
- `ruff>=0.11.5` - Linting and formatting
- `mkdocs>=1.4.2` - Documentation generation
- `mkdocs-material>=8.5.10` - Documentation theme
- `mkdocstrings[python]>=0.26.1` - API documentation
- Type stub packages for external dependencies

### Managing Dependencies

```bash
# Add new dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Update lock file
uv lock

# Verify consistency
uv lock --locked

# Upgrade dependencies
uv lock --upgrade
```

---

## Code Style Guidelines

### Formatting

- **Line length**: 120 characters
- **Indentation**: 4 spaces
- **String quotes**: Double quotes (enforced by Ruff)
- **Import order**: isort rules (stdlib → third-party → local)

### Type Hints

- Use modern type hints (Python 3.10+): `str | None` instead of `Optional[str]`
- Add return type annotations to all functions
- Use descriptive parameter names
- Use `Protocol` classes for configuration interfaces

### Docstrings

- Use Google/NumPy-style docstrings
- Include Parameters, Returns, and Raises sections
- Add type information in docstrings

### Error Handling

- Handle specific exceptions: `requests.RequestException`, `OSError`, `yaml.YAMLError`, etc.
- Provide user-friendly error messages via loguru
- Use structured logging levels (DEBUG, INFO, SUCCESS, ERROR)
- Return meaningful exit codes from main function

---

## Common Tasks

### Add a New Feature

1. Create feature branch: `git checkout -b feature/feature-name`
2. Write tests first (TDD approach)
3. Implement feature in appropriate core module
4. Run `make check` to ensure code quality
5. Run `make test` to verify tests pass
6. Update documentation if needed
7. Create pull request

### Fix a Bug

1. Write a failing test that reproduces the bug
2. Fix the bug in the code
3. Ensure test passes
4. Run `make check` and `make test`
5. Commit with descriptive message

### Update Documentation

1. Edit `.md` files in `docs/`
2. Run `make docs-test` to verify build
3. Run `make docs` to preview locally
4. Commit changes

### Release a New Version

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run `make check` and `make test`
4. Run `make build`
5. Create git tag and push

---

## Troubleshooting

### UV Command Not Found

- Ask user to install or provide absolute path to uv executable

### Permission Denied on .venv

```bash
# Recreate virtual environment
rm -rf .venv
uv sync
```

### Ruff Errors Not Auto-fixing

```bash
# Force fix
uv run ruff check --fix src/
uv run ruff format src/
```

### Type Checking Fails

```bash
# Check Ty configuration
uv run ty check --help

# Verify pre-commit is not interfering
uv run pre-commit run --all-files
```

### Test Coverage Low

```bash
# Generate detailed coverage report
uv run python -m pytest --cov --cov-report=html
open htmlcov/index.html

# Check specific file
uv run python -m pytest --cov=src/girsh/core/repos.py --cov-report=term-missing
```

---

## Resources

- **Project Repository**: <https://github.com/palto42/girsh>
- **Documentation**: <https://palto42.github.io/girsh/>
- **GitHub API**: <https://docs.github.com/en/rest/releases/releases>
- **UV Documentation**: <https://docs.astral.sh/uv/>
- **Ruff Documentation**: <https://docs.astral.sh/ruff/>
- **Ty Documentation**: <https://docs.astral.sh/ty/>
- **Pytest Documentation**: <https://docs.pytest.org/>
- **Loguru Documentation**: <https://loguru.readthedocs.io/>

---

## Writing Assistance

When writing code suggestions or tests for this project:

1. **Always use UV** for running Python: `uv run python -m pytest`
2. **Follow Ruff config** (line length 120, modern Python 3.10+ syntax)
3. **Include type hints** using modern syntax (`str | None`)
4. **Add Google-style docstrings** with Parameters, Returns, and Raises
5. **Use loguru** for logging with appropriate levels
6. **Handle file operations safely** with Path objects and proper error handling
7. **Mock external dependencies** (HTTP requests, file system) in tests
8. **Run `make check`** before suggesting code is ready
9. **Ensure tests pass**: `make test`
10. **Test code must pass Ruff and Ty**: All tests in `tests/` must comply with linting and type checking rules
    - Test files are subject to the same Ruff rules as source code
    - Type hints are required in all test functions and fixtures
    - Run `make check` to validate both source and test code quality</content>
<parameter name="filePath">/home/matthias/git/girsh/.github/copilot-instructions.md
