# Contributing

Thanks for contributing to `pro_sports_transactions`!

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
feat: add cloudscraper request handler
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
