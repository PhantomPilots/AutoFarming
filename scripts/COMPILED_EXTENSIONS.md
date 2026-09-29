# Compiled extension bundle paths

The extension loader accepts portable bundle paths and portable wheel members so the same verified bundle behaves consistently on Windows. Manifest file paths and wheel entries must use POSIX `/` separators and relative path components. Absolute paths, drive prefixes, `..` or `.` components, empty components, backslashes, colons (including NTFS alternate data streams), control characters, Windows reserved device names, and components ending in a dot or space are rejected. Wheel symbolic links are rejected.

`manifest.version` is also used as part of the local cache directory name. Keep it to a short ASCII version identifier beginning with a letter or digit and containing only letters, digits, `.`, `_`, `+`, or `-`. It cannot be a Windows reserved device name or end in a dot or space. The current supported bundles use ordinary dotted versions such as `1.4.1`.

The loader resolves every extraction target against the cache directory and refuses paths that resolve outside it. Keep wheel members unique under Windows case-insensitive path comparison, and do not package the reserved `.autofarmers-extension.json` cache marker.
