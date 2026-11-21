# Windows packaging qualification

Build the local candidate with `./scripts/build_portable.ps1` after installing
requirements-build-lock.txt in .venv. This bundles the desktop runtime and local FFmpeg;
it does not bundle .venv-ai or model weights. AI requires separate configuration.

The one-directory layout retains replaceable Qt libraries. The build produces a ZIP,
SHA256 checksum and per-file manifest under artifacts. These are local test candidates,
not approved releases. The installer definition targets per-user installation without admin;
compile packaging/installer.iss using Inno Setup after validating the portable candidate.

Release gates still open:
- Owner-selected application license and full third-party notices/source provision audit.
- Portable media import/playback/export and installer install/uninstall on clean Windows.
- Optional AI backend deployment and model provenance validation.
- Git remote configuration, reviewed CI build and explicit release approval.

The workflow is a manual syntax-check scaffold, not verified release automation.
No releases or artifacts are uploaded. Do not interpret local build success as clean-machine
compatibility, signing, licensing approval, or permission to distribute.

## Reproducible dependency discovery
The build script restricts PATH to the project interpreter and Windows directories while
PyInstaller runs, then restores the caller PATH. This prevents collection of same-named
native DLLs from unrelated installed tools. Use --clean to invalidate dependency analysis.
The first failed candidate contained Poppler's ICU DLL from the host application's PATH.
