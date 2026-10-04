# Contributing

Thanks for contributing to `pro_sports_transactions`!

## Pre-commit hooks

Each commit is checked by [pre-commit](https://pre-commit.com/) hooks defined in
[`.pre-commit-config.yaml`](.pre-commit-config.yaml):

- **[Betterleaks](https://github.com/betterleaks/betterleaks)** scans the staged
  changes for secrets (API keys, tokens, passwords).
- **[Semgrep](https://semgrep.dev/)** scans the staged Python, YAML, and
  Dockerfile changes for security issues (SAST).
- **[actionlint](https://github.com/rhysd/actionlint)** checks GitHub Actions
  workflows for errors.
- **[zizmor](https://docs.zizmor.sh/)** audits GitHub Actions workflows,
  `dependabot.yml`, and `.pre-commit-config.yaml` for security issues. Set
  `GH_TOKEN` (e.g. `GH_TOKEN=$(gh auth token)`) to add its online audits; CI
  always runs them.

The hooks run from [`.githooks/pre-commit`](.githooks/pre-commit), which works
both inside the dev container and directly on your machine. The dev container
enables it for you. Otherwise, enable it once per clone with:

```
git config core.hooksPath .githooks
```

The only requirement is [uv](https://docs.astral.sh/uv/) (or `pre-commit`)
on your PATH. If you use the dev container, the setting is shared with your
machine, so commits from a host terminal, GitHub Desktop, or an IDE outside the
container are checked as well. Don't use `pre-commit install`: the hook it
generates is tied to one Python environment, so it breaks commits made from
the other side of the container. Setting `core.hooksPath` also means git stops
running any hooks of your own in `.git/hooks`; move them into `.githooks` (or
call them from it) if you want to keep them.

The first commit afterwards takes a minute while pre-commit builds the tools;
later commits take a few seconds. To run every hook against the whole tree:

```
uv run pre-commit run --all-files
```

CI runs the same hooks on every pull request, so a commit made with
`--no-verify` is still checked. CI also runs two scans that are not hooks:
Betterleaks over the **full git history**, and
[Trivy](https://trivy.dev/) over `uv.lock` (known-vulnerable dependencies) and
the dev container Dockerfile (misconfigurations). Trivy's settings are in
[`trivy.yaml`](trivy.yaml); to run it locally,
[install Trivy](https://trivy.dev/latest/getting-started/installation/) and run
`trivy fs .` from the repo root.

Trivy and Semgrep also run weekly and on every push to `main`
([Security](.github/workflows/security.yml) workflow), because new CVEs and
updated Semgrep rules can turn up findings without any code change. Their
findings are listed under the repository's **Security > Code scanning** tab,
and a failing run opens a "Security scan failing on main" issue.

### False positives

Confirm the finding really is harmless, then suppress it as narrowly as
possible, with a comment saying why:

| Tool        | Suppress with                                                                        |
| ----------- | ------------------------------------------------------------------------------------ |
| Betterleaks | add the finding's fingerprint to [`.betterleaksignore`](.betterleaksignore)          |
| Semgrep     | a `# nosemgrep: <rule-id>` comment on the flagged line                               |
| zizmor      | a `# zizmor: ignore[<audit>]` comment on the flagged line                            |
| Trivy       | add the vulnerability ID to a `.trivyignore` file (prefer upgrading the package)     |

## Pull request titles

This repository **squash-merges** pull requests, so the **PR title becomes the
commit subject on `main`**. PR titles must follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) and
are validated automatically by the [PR Title](.github/workflows/pr-title.yml)
workflow. Individual commit messages within a PR are collapsed at squash and are
not policed — only the title matters.

The format is:

```
<type>[optional scope]: <description>
```

Examples:

```
feat: add nodriver request handler
fix(search): handle empty response body
docs: document the unflare handler
chore(deps): bump aiohttp to 3.13.3
```

### Allowed types

| Type       | Use for                                                        |
| ---------- | -------------------------------------------------------------- |
| `feat`     | A new feature                                                  |
| `fix`      | A bug fix                                                      |
| `docs`     | Documentation only changes                                     |
| `style`    | Formatting, whitespace — no code-behavior change               |
| `refactor` | A code change that neither fixes a bug nor adds a feature      |
| `perf`     | A change that improves performance                             |
| `test`     | Adding or correcting tests                                     |
| `build`    | Changes to the build system or dependencies                   |
| `ci`       | Changes to CI configuration and scripts                        |
| `chore`    | Other changes that don't modify `src` or `test` files         |
| `revert`   | Reverts a previous commit                                      |

A breaking change is marked with a `!` after the type/scope (e.g. `feat!:`) or a
`BREAKING CHANGE:` footer.

### How titles drive releases

Releases are automated by
[release-please](https://github.com/googleapis/release-please) (see
[`release.yml`](.github/workflows/release.yml)), so the PR title also decides
the next version and the changelog entry:

| Title                                                              | Version bump | Changelog section        |
| ------------------------------------------------------------------ | ------------ | ------------------------ |
| `feat!:` / `BREAKING CHANGE:`                                      | major        | ⚠ BREAKING CHANGES       |
| `feat:`                                                            | minor        | Features                 |
| `fix:`                                                             | patch        | Bug Fixes                |
| `perf:`                                                            | patch        | Performance Improvements |
| `revert:`                                                          | patch        | Reverts                  |
| `build:`, `chore:`, `ci:`, `docs:`, `refactor:`, `style:`, `test:` | none         | not listed               |

The last row's types never trigger a release on their own. If a release is
already pending, they're included in it but left out of the changelog. That
includes `docs:`: documentation (and the README on PyPI) ships with the next
code release (set in `changelog-sections` in `release-please-config.json`).

Write the title (and description) as the changelog line a user should read.

## Releasing

There's no manual version bump, tag, or upload:

1. Merge pull requests to `main` as usual. After each merge, release-please
   opens or updates a **`chore(main): release X.Y.Z`** pull request that bumps
   the version in `pyproject.toml` and `uv.lock` and prepends the new section to
   `CHANGELOG.md`.
2. When you're ready to release, review that PR (edit its changelog section or
   description if needed; the description becomes the GitHub release notes)
   and merge it. Edits are overwritten if anything else merges to `main` first.
3. The merge tags `vX.Y.Z`, creates the GitHub release, publishes the sdist and
   wheel to [PyPI](https://pypi.org/project/pro_sports_transactions/), and
   attaches them to the GitHub release.

To force a specific version, merge a commit to `main` whose body contains a
`Release-As: X.Y.Z` footer.
