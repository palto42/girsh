# Changelog

## Version 0.1.33

- Update packe dependencies to fix security vulnerabilities
    - **requests**: upgraded to **2.33.1**
        - Fixed credential leak via malicious `.netrc` URLs
          (CVE-2024-47081)
        - Fixed insecure temporary file reuse in `extract_zipped_paths()`
          (CVE-2026-25645)
    - **urllib3**: upgraded to **2.6.3**
        - Fixed improper handling of highly compressed data in streaming API
          (CVE-2025-66471)
        - Fixed decompression-bomb bypass via HTTP redirects
          (CVE-2026-21441)
        - Fixed uncontrolled redirects in browser/Node.js environments
          (CVE-2025-50182)
        - Fixed unbounded decompression chain vulnerability
          (CVE-2025-66418)
        - Fixed redirects not disabled when retries are off
          (CVE-2025-50181)
- Added "uv audit" in .pre-commit-config.yaml to always check for known vulnerabilities
- Fixed some minor ruff checks

## Version 0.1.32

- Added missing config template to package.

## Version 0.1.31

- Added pre/post command prefix to run the command in a shell instead of simple command sequence.

## Version 0.1.30

- This is the first public release which provides the functions as described in the docs files.
