# Configuration

## Package installation settings

The general settings and a list of repositories are defined in a YAML config file (default `~/.config/girsh_config.yaml`).
It can be created from template using the "--edit" option.

The configuration file should have the following structure:

```yaml title="girsh_config.yaml"
general:
  # Optional: Base folder where binaries will be installed.
  # For non-root users, this should usually be "~/.local/bin"
  bin_base_folder: "/usr/local/bin"

  # Optional: Path to the cache file where installed versions and binary names
  # are stored. If not provided, it defaults to "~/.cache/girsh/girsh.yaml"
  installed_file: "/home/your_username/.installed/girsh/girsh.yaml"

  # Optional: Path to the download folder.
  # If not provided, it defaults to "~/.installed/girsh/downloads"
  download_dir: Path = "/my/custom/bin"

  # Optional: Regex pattern to select the release asset, defaults to ".*x86_64.*(gz|zip)$"
  package_pattern: ".*aarch64.*(gz|zip)$"

  # Optional: Package base folder (for multi-file packages)
  # If not provided, it defaults to "~/.local/share/girsh" or "/opt/girsh"
  package_base_folder: "/my/Packages"

repositories:
  # Dictionary of git repositories from which the released binary should be installed
  owner/repository-name:
    # Optional: Comment about the installed package
    comment: This is an interesting tool
    # Optional: Regex pattern to select the release asset, defaults to ".*(gz|zip)"
    package_pattern: str = ".*amd_64.*gz"
    # Optional: Regex pattern to filter the extracted files to identify the binary.
    # Optional: Regex pattern to filter the extracted files to identify the binary.
    # If the same file name is present in multiple folders, include a (sub-)path.
    filter_pattern: "bin/my_binary$"
    # Optional: Renaming rule. If provided, the matching binary will be renamed
    # to this name before installation.
    binary_name: "my-renamed-binary"
    # Optional: Pin to specific version (git tag)
    version: v0.41.2
    # Optional: Flag that the packe is not a single binary
    multi_file: true
    # Optional: Pre-update/uninstall commands
    pre_update_commands:
      - echo "Pre-update command 1"
      - "%confirm_default_no% Continue to install?"
      - "%stop_processes% my-renamed-binary"
    # Optional: Post-install/update commands
    post_update_commands:
      - echo "Post-update command 1"
      - echo "Post-update command 2"
    # Optional: Download URL template using `{version}` as a placeholder for the release tag
    download_url: https://package/download/{version}/linux-x64/stable
```

### Commands

#### Option to continue in case of failure

By default the installation or update for a repository will fail if one of the defined commands returns non-zero exit code.
If the command is prefixed with a `|`, then errors for this command are ignored.

Example: `|sh -c 'exit 42'`

#### Comments

Commands can be disabled as comment using `#` prefix, also within an explicit string.

Example:

```yaml
pre_update_commands:
  -  #echo "Pre-update command 1"
  - "#%confirm_default_no% Continue to install?"
```

#### Macros

The pre- and post-update commands also support some macros.
Macro commands must be at the beginning of the command string and are encapsulated with `%`, e.g. `%my_macro%`.
The string after the macro command name is passed to the macro function and must be separated by one space from the macro command.

If the macro returns `False`, the command execution and further processing of the related repository is cancelled with an error.

- **Supported macros:**
  - `%confirm_default_yes%`
    - Prompts the user with a yes/no question and returns True if the user doesn't explicitly answers "n" (no).
    - Argument: Question string.
    - Example: `%confirm_default_yes% Install program?`
  - `%confirm_default_no%`
    - Prompts the user with a yes/no question and returns True if the user explicitly answers "y" (yes).
    - Argument: Question string.
    - Example: `%confirm_default_no% Kill program?`
  - `%stop_processes%`
    - Terminate all running processes for of given program.
    - Argument: program name
    - Example: `%stop_processes% my_program`
