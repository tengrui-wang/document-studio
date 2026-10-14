# Document Studio development rules

- Modify files only in this project by default. Use the existing Conda interpreter and project-local `.venv`; do not modify shared environments or other projects without authorization.
- Reuse installed software and mature open-source libraries. Do not reinstall available software or introduce unrelated refactoring.
- Implement clear tasks directly. Run only necessary intermediate checks; full acceptance is for a final version.
- Keep `README.md`, `PROJECT_STATUS.md`, and `PROGRESS.md` current. Read these before resuming work.
- Use this project's separate Git repository for important commits. Push only when requested or within existing explicit session authorization.
- Obtain authorization before upgrading shared environments, deleting user files, or making system-level changes. Respect sandbox restrictions; never enable Full Access or bypass controls.
- Never commit API keys, private documents, task history, checkpoint translations or local build data.
- This is a 0.1.0 core preview. Do not claim OCR, original-layout scientific PDF translation, complete layout preservation, or full final acceptance is implemented.
