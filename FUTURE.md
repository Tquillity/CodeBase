# Future Work

## Gitignore Engine
CodeBase now reparses the active repository's root `.gitignore` on each scan, and version `7.3.0` fixes rooted patterns such as `/.cypress-cache/`. The next step is to replace the remaining custom ignore matching with a fully Git-compatible engine so the app behaves exactly like Git and avoids future token bombs.

Planned work:
- Replace the hand-rolled ignore matcher with a Git-compatible matcher such as `pathspec`.
- Support rooted rules, directory rules, globs, and negation (`!`) with Git-accurate behavior.
- Support nested `.gitignore` files inside subdirectories, not just the repository root.
- Rebuild ignore rules on every refresh so new ignore entries are picked up immediately.
- Optionally detect `.gitignore` changes in the loaded repository and prompt for or trigger a refresh.
- Add regression tests for large generated/cache folders such as `.cypress-cache`, `.next`, `node_modules`, `dist`, and coverage outputs.

Why this matters:
- Prevent generated folders from inflating file counts and token counts.
- Keep CodeBase behavior predictable for users who already maintain `.gitignore`.
- Reduce the need for manual exclusion toggles when repository tooling changes.
