# girsh - Git Install Released Software Helper

![python version](https://img.shields.io/badge/python-3.10+-blue.svg)
[![PyPI](https://img.shields.io/pypi/v/girsh)](https://pypi.org/project/girsh)
[![Build status](https://img.shields.io/github/actions/workflow/status/palto42/girsh/main.yml?branch=main)](https://github.com/palto42/girsh/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/palto42/girsh/branch/main/graph/badge.svg)](https://codecov.io/gh/palto42/girsh)
[![Commit activity](https://img.shields.io/github/commit-activity/m/palto42/girsh)](https://img.shields.io/github/commit-activity/m/palto42/girsh)
[![License](https://img.shields.io/github/license/palto42/girsh)](https://img.shields.io/github/license/palto42/girsh)

This tool downloads and installs released binaries from GitHub repositories on Linux type systems.

- **Github repository**: <https://github.com/palto42/girsh/>
- **Documentation** <https://palto42.github.io/girsh/>

## Description

This script reads input from a YAML file to define GitHub release pages,
binary package patterns, and extraction rules.
The script handles downloads, extraction, renaming,
and copying to the appropriate binary folder based on user permissions.

The script checks whether the user has root privileges to copy binaries to /usr/local/bin;
otherwise, it defaults to ~/.local/bin.

## Development

### 1. Clone the repository

First, clone the project repository, and then run the following commands:

```text

git clone ssh://git@github.com:palto42/girsh.git
```

### 2. Set Up Your Development Environment

Then, install the environment and the pre-commit hooks with

```text
make install
```

### 3. Run the pre-commit hooks

Initially, the CI/CD pipeline might be failing due to formatting issues. To resolve those run:

```bash
uv run pre-commit run -a
```

### 4. Commit the changes

Lastly, commit the changes made by the two steps above to your repository.

```bash
git add .
git commit -m 'Fix formatting issues'
git push origin main
```

You are now ready to start development on your project!
The CI/CD pipeline will be triggered when you open a pull request, merge to main, or when you create a new release.

To finalize the set-up for publishing to PyPI, see [here](https://fpgmaas.github.io/cookiecutter-uv/features/publishing/#set-up-for-pypi).
For activating the automatic documentation with MkDocs, see [here](https://fpgmaas.github.io/cookiecutter-uv/features/mkdocs/#enabling-the-documentation-on-github).
To enable the code coverage reports, see [here](https://fpgmaas.github.io/cookiecutter-uv/features/codecov/).

## Releasing a new version

- Create an API Token on [PyPI](https://pypi.org/).
- Add the API Token to your projects secrets with the name `PYPI_TOKEN` by visiting [this page](https://github.com/palto42/girsh/settings/secrets/actions/new).
- Create a [new release](https://github.com/palto42/girsh/releases/new) on Github.
- Create a new tag in the form `*.*.*`.

For more details, see [here](https://fpgmaas.github.io/cookiecutter-uv/features/cicd/#how-to-trigger-a-release).

### 3. Use make commands

| make command      | Description                                                      |
| ----------------- | ---------------------------------------------------------------- |
| install           | Install the virtual environment and install the pre-commit hooks |
| check             | Run code quality tools.                                          |
| test              | Test the code with pytest                                        |
| build             | Build wheel file                                                 |
| clean-build       | Clean build artifacts                                            |
| publish           | Publish a release to PyPI.                                       |
| build-and-publish | Build and publish.                                               |
| docs              | Build and serve the documentation                                |
| docs-test         | Test if documentation can be built without warnings or errors    |

**Note**: `make check` validates the files stages with `git add`.
Otherwise it may show only "(no files to check)Skipped" messages.
