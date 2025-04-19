# Usage

```text
usage: girsh [-h] [-r BINARY [BINARY ...] | -u | --uninstall-all | --clean | -s | -e] [-c CONFIG] [-d] [-v] [-g] [-V]

Git Install Released Software Helper

options:
  -h, --help            show this help message and exit
  -r BINARY [BINARY ...], --reinstall BINARY [BINARY ...]
                        Force re-installation even if version unchanged
  -u, --uninstall       Uninstall previously installed binary if not present in config anymore
  --uninstall-all       Uninstall all previously installed binaries
  --clean               Remove the downloads folder and exit
  -s, --show            Show config and currently installed binaries
  -e, --edit            Open the config file in the default editor
  -c CONFIG, --config CONFIG
                        Path to config file, defaults to ~/.config/girsh.yaml
  -d, --dry-run         Run without actually installing or removing any files.
  -v, --verbose         Increase output verbosity (up to 3 times)
  -g, --global          Install as root at system level
  -V, --version         show program's version number and exit
```

## Functions

### Install or update packages

Run the script with your default configuration file:

```text
girsh
```

This command processes each repository entry in the configuration,
downloads the latest release asset (if a new version is available),
extracts the asset, renames it (if configured),
and installs the binary to the specified bin_base_folder.

Example:

```text
$ girsh

mrjackwills/oxker: skipped
jesseduffield/lazydocker updated from v0.23.0 to v0.24.1
containers/podman-tui installed version v1.4.0
===============================
Summary:
  skipped: 1
  updated: 1
  installed: 1
```

### Show installed programs

Example:

```text
$ girsh --show

Currently installed binaries:
+--------------------------+----------------------------------------------+------------+---------+
| Repository               | Comment                                      | Binary     | Tag     |
+--------------------------+----------------------------------------------+------------+---------+
| containers/podman-tui    | Go TUI for Podman environment.               | podman-tui | v1.4.0  |
| jesseduffield/lazydocker | Go TUI for both docker and docker-compose    | lazydocker | v0.24.1 |
| mrjackwills/oxker        | Rust tui to view & control docker containers | oxker      | v0.10.0 |
+--------------------------+----------------------------------------------+------------+---------+
```

### Use custom config file

Run the script with your custom configuration file:

```text
girsh --config my_config.yaml
```

### Force Re-installation

To force re-installation of a binary even if the installed version matches the latest release, use the `--reinstall` option:

```text
girsh --reinstall
```

### Uninstall Installed Binaries

If some repository has been removed from the config file and the binary should be removed, use the `--uninstall` option:

```text
girsh --uninstall
```

To uninstall all binaries installed by the script (tracked in the installation logs), use the `--uninstall-all` option:

```text
girsh --uninstall-all
```

This command will remove all binaries from the target installation folder that are tracked
in the installation logs and then clear the installation logs.

### Clean Temporary Downloads

To remove the downloads folder (used for temporary storage) and exit:

```text
girsh --clean
```

### Script output

The script uses Loguru for logging. By default, it logs success messages to stdout.
For more detailed output the verbosity can be increase:

```text
girsh -v
```

The verbosity can be increased up to 3 time, e.g. `girsh -vvv` for trace logs.

## Example Workflow

Create your `girsh_config.yaml` from template.

```text
girsh --edit

The file '/home/user_name/.config/girsh.yaml' does not exist. Do you want to create it? (y/N):y
```

Run the installer:

```text
girsh
```

To update binaries when new versions are released, simply re-run the installer.
The script will check the installation logs and only download and install if
there's a version change(unless `--reinstall` is specified).

If you want to remove all installed binaries:

```text
girsh --uninstall-all
```

To clean up temporary downloads:

```text
girsh --clean
```
