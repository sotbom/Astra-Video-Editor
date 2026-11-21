# Astra development instructions

Read SKILL.md (master specification), PROGRESS.md, README.md and relevant modules before edits.
Follow the roadmap in order. Keep UI, media processing, project state and export separate.
Use the local .venv and pinned requirements-lock.txt. Keep Phase 4 AI dependencies isolated
in .venv-ai with requirements-ai-lock.txt; do not install unrelated AI stacks.
Use background jobs for probing/processing and Qt signals for GUI updates.
Use subprocess argument lists, bounded timeouts, and generated test assets.
Run Ruff and pytest, launch the desktop application, and verify changed behavior.
Update PROGRESS.md with evidence and limitations; never equate file creation with completion.
Preserve source media. Do not publish releases before packaging and licensing verification.
