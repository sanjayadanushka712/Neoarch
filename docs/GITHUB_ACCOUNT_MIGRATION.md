# Moving the project off a risky account

The project currently lives on `sanjayadanushka712`, a personal account created after
the original one (`dsanjaya712@gmail.com`) was suspended. Two personal accounts
plus a suspended one is the pattern GitHub treats as evasion, and the whole
project — repo, releases, Actions secrets, the AUR publish workflow — goes with
that account if it is restricted.

The fix is to end up with **one personal account** and **one organization**:

| Purpose | Account |
| --- | --- |
| You, as a person (job interviews, profile, contributions) | `sanjayadanushka712` |
| The project (repo, releases, AUR workflow) | an Organization |

## Option A — convert `sanjayadanushka712` into an Organization (recommended)

The URL `github.com/sanjayadanushka712/Neoarch` stays exactly the same, so the AUR
source, the README links and the website keep working.

1. Log in to `sanjayadanushka712` and add your SSH key under
   **Settings → SSH and GPG keys** (organisation owners need their own key).
2. Log in to `sanjayadanushka712` → **Settings → Account** → scroll to
   **Transform your personal account into an organization** → choose
   `sanjayadanushka712` as the organisation name and confirm.
3. The account is now an organisation and you are its owner. In
   **Organisation settings → People → Invite member**, invite
   `sanjayadanushka712` with the **Owner** role, then accept the invitation
   from the personal account.
4. Add a trusted co-maintainer as a second owner if you have one — that way a
   single flagged account cannot lock the organisation.
5. In the repository: **Settings → Secrets and variables → Actions** — check
   that `AUR_SSH_KEY` is still present after the conversion (repo secrets stay
   with the repo).
6. Point your local clone at the personal account's credentials:
   ```bash
   git remote set-url origin git@github.com:sanjayadanushka712/Neoarch.git
   ```
   (the old GitHub SSH host alias no longer works — organisations cannot
   log in over SSH).

After this the project still lives at `github.com/sanjayadanushka712/Neoarch`, but
`sanjayadanushka712` is the only personal account involved.

## Option B — create a new organisation and transfer the repo

Cleaner name (for example `neoarch-app`), but the repository URL changes.
GitHub redirects the old URL, so the AUR tarball URL keeps resolving, but
update these afterwards:

- `packaging/PKGBUILD.stable` → `url=...`
- `.github/workflows/aur-*.yml` → clone/commit URLs
- README badges and `neoarch.dpdns.org` links

1. With `sanjayadanushka712`: **+ → New organisation** → free plan → create it.
2. Organization → **People** → invite `sanjayadanushka712` as **Owner** (needed to
   transfer out of the old account), or use **Settings → Transfer ownership**
   on the repo.
3. Transfer `Neoarch` into the new organisation.
4. Once the transfer is done, `sanjayadanushka712` is a personal account with no
   purpose — stop using it and do not log in from the same machine/browser as
   the personal account.

## Commit identity

Every commit should be authored by the account you want interviews to see.
The repository is already configured for that locally:

```bash
git config user.name  "Sanjaya Danushka"
git config user.email "345766647+sanjayadanushka712@users.noreply.github.com"
```

Do **not** use `dsanjaya712@gmail.com` for new commits — that address belongs to
the suspended account and links the new work to it.

## Independent mirror (do this today)

1. Create `https://codeberg.org/<you>/Neoarch` (empty, no README).
2. Codeberg → **Settings → Applications → Generate new token** with
   `repository:write`.
3. GitHub repo → **Settings → Secrets and variables → Actions → New repository
   secret**:
   - `CODEBERG_USER` — your Codeberg username
   - `CODEBERG_TOKEN` — the token from step 2
4. Push to `dev` or `main`: `.github/workflows/mirror-codeberg.yml` copies all
   branches and tags to Codeberg automatically.

If GitHub disappears tomorrow, `git clone https://codeberg.org/<you>/Neoarch`
and the AUR package can be rebuilt by changing one `source=` line.

## Things that stay safe

- **AUR** (`aur.archlinux.org/packages/neoarch`) is a separate system with its
  own account — a GitHub suspension does not touch it.
- **The website** (`neoarch.dpdns.org`) and the AUR package page are proof of
  the project for interviews that does not depend on GitHub.
- Old commits authored with `dsanjaya712@gmail.com` stay in history; only new
  commits need the new identity.

## Do not

- Do not create a third account.
- Do not add the suspended account as collaborator/owner anywhere.
- Do not reuse its email, SSH key or personal access token.
- Do not hand your PAT around in plain text — `~/.git-credentials-neoarch`
  stores the current ones unencrypted; move to SSH keys instead.
