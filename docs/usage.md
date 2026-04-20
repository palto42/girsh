# Usage

```text
usage: girsh [-h] [-r BINARY [BINARY ...] | -u | --uninstall-all | --clean | -s | -e | --test-proxy] [-c CONFIG] [-d] [-v] [-g] [-p PROXY] [-V]

Git Install Released Software Helper

options:
  -h, --help            show this help message and exit
  -r, --reinstall BINARY [BINARY ...]
                        Force re-installation even if version unchanged
  -u, --uninstall       Uninstall previously installed binary if not present in config anymore
  --uninstall-all       Uninstall all previously installed binaries
  --clean               Remove the downloads folder and exit
  -s, --show            Show config and currently installed binaries
  -e, --edit            Open the config file in the default editor
  --test-proxy          Test proxy configuration by making a request
  -c, --config CONFIG   Path to config file, defaults to ~/.config/girsh.yaml
  -d, --dry-run         Run without actually installing or removing any files.
  -v, --verbose         Increase output verbosity (up to 3 times)
  -g, --global          Install as root at system level
  -p, --proxy PROXY     Proxy URL for downloading files (e.g., http://proxy.example.com:8080)
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

## Using a Proxy for Downloads

If you need to download assets through an HTTP or HTTPS proxy, `girsh` supports proxy configuration both via command-line arguments and configuration files.

### Proxy Format

The proxy URL format is flexible and supports HTTP and HTTPS proxies:

- **Scheme**: `http://` or `https://` (defaults to `http://` if omitted)
- **Authentication**: Optional `username:password@` for proxy authentication
- **Host**: Hostname or IP address (required)
- **Port**: Optional port number (1-65535, defaults to 80 for HTTP or 443 for HTTPS)

### Proxy Configuration Methods

#### 1. Command-line Argument

Use the `-p` or `--proxy` flag:

```text
girsh --proxy http://proxy.example.com:8080
```

With authentication:

```text
girsh --proxy http://user:password@proxy.example.com:3128
```

#### 2. Configuration File

Add the `proxy` setting under the `general` section in your `~/.config/girsh.yaml`:

```yaml
general:
  proxy: http://proxy.example.com:8080
  # or with authentication:
  proxy: user:password@proxy.example.com:3128
  # or without scheme (defaults to http://):
  proxy: proxy.example.com:8080
```

#### 3. Supported Proxy Schemes

Only HTTP and HTTPS proxies are supported:

- **HTTP Proxy**: `http://proxy.example.com:8080` - For both HTTP and HTTPS connections
- **HTTPS Proxy**: `https://proxy.example.com:8080` - Encrypted connection to proxy

**Note**: SOCKS proxies (SOCKS4/SOCKS5) are not currently supported.

### Proxy Authentication

If your proxy requires authentication, include credentials in the URL:

- **Format**: `scheme://username:password@host:port`
- **Example**: `http://john:secret@proxy.internal:3128`
- **Warning**: Credentials in config files are stored in plaintext. Ensure proper file permissions (mode 600).

### Troubleshooting Proxy Issues

#### Proxy Connection Failures

If you see proxy-related errors:

```text
Error fetching release info: Proxy error fetching release info for owner/repo: ...
```

**Solutions**:

1. Verify proxy URL is correct: `http://proxy.example.com:8080`
2. Check proxy port is accessible: Use `telnet proxy.example.com 8080` or equivalent
3. Ensure no firewall blocks outbound connections to proxy
4. Check proxy logs for rejected connections

#### Proxy Authentication Errors

If you see authentication errors:

```text
Proxy authentication required. Check proxy credentials.
```

**Solutions**:

1. Verify username and password are correct
2. Check if credentials need URL encoding (special characters)
3. Test credentials separately against the proxy
4. Ensure proxy accepts the authentication method

#### Timeout Issues

If downloads timeout through proxy:

```text
Connection timeout downloading ...: ...
```

**Solutions**:

1. Increase timeout by checking proxy performance
2. Try direct connection (disable proxy) to isolate the issue
3. Check if proxy has bandwidth limits
4. Verify network path to proxy server

### Example: Corporate Proxy Setup

For a typical corporate environment:

```bash
# In ~/.config/girsh.yaml
general:
  proxy: http://proxy.corp.internal:3128

# Or via command line
girsh --proxy http://proxy.corp.internal:3128
```

With authentication:

```bash
general:
  proxy: http://username:password@proxy.corp.internal:3128
```
