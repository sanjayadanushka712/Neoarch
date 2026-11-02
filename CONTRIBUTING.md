# Contributing

## Branch model

- `main` — stable releases.
- `beta` — integration branch for the next release.
- Feature branches — short-lived branches created from `beta`.

Use a descriptive prefix:

- `feat/` for features
- `fix/` for bug fixes
- `chore/` for maintenance
- `docs/` for documentation

## Workflow

1. Update `beta`:

   ```bash
   git switch beta
   git pull --ff-only github beta
   ```

2. Create a feature branch:

   ```bash
   git switch -c feat/short-name
   ```

3. Commit small, focused changes.

4. Push the branch and open a pull request into `beta`:

   ```bash
   git push -u github feat/short-name
   gh pr create --base beta --head feat/short-name
   ```

5. Request a review from a collaborator.

6. Merge with a merge commit. Avoid squash merging when co-author trailers
   need to be preserved.

7. Delete the feature branch after merging.

Do not push directly to `beta`; branch protection requires a pull request.

## Co-authored commits

Pair Extraordinaire credits the account named in the commit trailer, not the
primary author. Add co-authors only for real paired work:

```text
Co-authored-by: Name <id+username@users.noreply.github.com>
```

The trailer must be in the commit message, separated from the body by a blank
line. Pull Shark requires pull requests opened by your account that are
merged.
