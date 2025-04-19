# girsh

[![Release](https://img.shields.io/github/v/release/palto42/girsh)](https://img.shields.io/github/v/release/palto42/girsh)
[![Build status](https://img.shields.io/github/actions/workflow/status/palto42/girsh/main.yml?branch=main)](https://github.com/palto42/girsh/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/palto42/girsh)](https://img.shields.io/github/commit-activity/m/palto42/girsh)
[![License](https://img.shields.io/github/license/palto42/girsh)](https://img.shields.io/github/license/palto42/girsh)

The Git Installer is a Python script designed to automate the process of downloading, extracting,
and installing binary releases from GitHub repositories.
It also supports uninstalling previously installed binaries and caching version information to avoid redundant installations.

## Features

- **Download Releases** -
  Downloads assets from the latest GitHub release based on a regex pattern.
- **Extract Archives Securely** -
  Supports native binaries as well as extraction of `.tar.gz`/`.tgz`, `.zip` and `.tar.bz2`/`.bz2` archives
  with simple or pattern based search of the contained binary.
- **Optional Renaming** -
  Allows you to specify a filter and renaming rule to select the correct binary from an extracted archive.
- **Installation and Re-installation** -
  Automatically copies the binary to the appropriate binary folder based on user privileges
  (e.g., /`usr/local/bin` for root, `~/.local/bin` for non-root). Use the `--reinstall` option to force a re-install.
- **Uninstallation** -
  Provides an uninstall option (`--uninstall-all`) that removes all binaries installed by the script,
  based on the cached information.
  Individual packages can be uninstalled by removing them from the settings file and then running `girsh --uninstall`.
- **Install logs** -
  The script tracks installed versions and binary names in a installed settings file,
  avoiding unnecessary downloads and installations if the version hasn’t changed.
- **Pre- and post update/uninstall commands**
  Optional commands to be executed before update/uninstall and after update,
  e.g. stop/start process

For more detail see [Config](config.md) and [Usage](usage.md).
