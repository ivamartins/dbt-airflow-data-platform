# Documentation & Contribution Conventions

This file defines the standards used across all Code Solutions open source projects.

## File naming standard

| File | Language | Notes |
|------|----------|-------|
| `README.md` | English (default) | GitHub's default; visible when repo is opened |
| `README.pt-BR.md` | Portuguese (Brazil) | Mirror of the English README |
| `CONTRIBUTING.md` | English | Contribution guide and project conventions |
| `CHANGELOG.md` | English | Notable changes per release |
| `LICENSE` | English (legal) | Project license |

## Code comments

- **All code comments in English** (Python docstrings, `#`, `""" """`)
- Comments explain **why**, not what
- Public APIs always have a docstring
- Example:
  ```python
  # Persists the document asynchronously to avoid blocking the request thread.
  def save(doc: Document) -> Future[None]:
      ...
  ```

## Commit messages

- Written in **English**
- Use the imperative mood ("Add", not "Added")
- Format: short summary (≤72 chars) + optional body
- Prefix examples: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Branch names

- `main` — production
- `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`, `chore/<short-name>`

## PR / commit hygiene

- One logical change per commit
- Tests pass before commit (`pytest`, `dbt test`)
- Public API changes documented in the commit body

## When in doubt

- Follow the convention in the existing repo
- If it's a new project, copy this file as-is
