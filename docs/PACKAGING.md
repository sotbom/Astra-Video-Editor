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

## Download a GitHub Actions test build
Open Actions > Build Windows test release > Run workflow on main. Leave the draft-release
option checked to attach the ZIP to a draft prerelease. After a green run, download the
Astra-Windows-test artifact from the run page, or open the draft under Releases as the owner.
Extract the artifact ZIP, then extract the portable ZIP inside it. Run AstraVideoEditor.exe
with the entire _internal directory beside it. No Python installation is required.
The build is unsigned; AI dependencies and models are separate. Keep the release as a draft
until redistribution checks are complete. The workflow performs core/render tests and a
frozen main-window startup check, not a complete clean-PC playback/export qualification.
