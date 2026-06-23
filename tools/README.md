# tools — docs sync pipeline

The bundled references under [`skills/nestjs/references/`](../skills/nestjs/references/) are
**generated**, not hand-written. They are produced from the upstream
[nestjs/docs.nestjs.com](https://github.com/nestjs/docs.nestjs.com) repository and kept in sync
automatically. Don't edit `references/` by hand — edit the converter and rebuild.

NestJS's practitioner docs live in a dedicated Angular docs site; the prose pages are authored as
Markdown under `content/` in a small custom dialect (TS/JS code toggles, `> info` callouts, promo
banners). The pipeline reads that `content/` tree.

## Scripts (stdlib-only Python 3, no dependencies)

### `build_references.py`

Converts a checkout of `docs.nestjs.com` into the reference bundle: the `content/` Markdown is
cleaned into faithful plain Markdown, the directory tree is mirrored under `references/`, and
`CONTENTS.md` (navigation in the site's sidebar order) and `LICENSE` (copied from upstream) are
regenerated. Deterministic — same input produces byte-identical output.

```bash
git clone --depth 1 https://github.com/nestjs/docs.nestjs.com.git /tmp/docs.nestjs.com
python3 tools/build_references.py --docs-repo /tmp/docs.nestjs.com --out skills/nestjs/references
```

It renders NestJS's doc dialect: `@@filename(name)` / `@@switch` code fences (the canonical
**TypeScript** half is kept, the filename becomes a `title="name.ts"` info-string, and the
`@@switch` JavaScript half is dropped), `> info`/`> warning`/`> error` blockquote callouts (kept
verbatim — they are already valid Markdown), `<figure><img src="/assets/…">` (turned into Markdown
images on the live site), `<app-banner-*>` promo tags (stripped), `{{ '{' }}` mustache brace
escapes (unescaped to literal braces), and doc-relative links (absolutized to
`https://docs.nestjs.com/…`). Headings are promoted by two levels so each page has one H1. Code
fences are protected end-to-end, so `#` comments and `<Generic>` types inside examples are never
altered. Each page keeps a `> Source:` link to its upstream file on GitHub.

The script only ever writes `references/` — it does not touch the sync cache key (`.source-commit`
at the repo root), which the workflow manages so nothing build-related leaks into the shipped
`skills/` bundle.

### `check_references.py`

A guard that fails (exit 1) if the generated bundle has defects: empty/short files, missing H1,
unbalanced code fences, broken intra-bundle links, or **any leftover dialect token outside code** —
`@@filename`/`@@switch` directives, `<app-banner-*>` tags, or `{{ '{' }}` mustache escapes, each a
signal that upstream introduced syntax the converter doesn't handle yet. (`#` comments and types
_inside_ ```code fences are intentionally ignored.)

```bash
python3 tools/check_references.py skills/nestjs/references
```

## Automation

[`.github/workflows/sync-docs.yml`](../.github/workflows/sync-docs.yml) runs daily (and on demand).
It first does a cheap `git ls-remote` to read the upstream HEAD **without cloning** and compares it
to `.source-commit` (a one-line file at the repo root). If they match, the run stops there (no
clone, no rebuild, no PR). Otherwise it clones the upstream docs repo, rebuilds the references,
writes the new commit to `.source-commit`, runs the guard, and opens a PR. If the guard finds an
unhandled token, the PR is labeled `needs-converter-update` so the converter is fixed before merge.

`.source-commit` lives at the repo root (not under `skills/`, which ships to end users) and moves
only inside a sync PR, so it never causes day-to-day churn — most days the gate matches and the job
is a no-op.

### Repo settings required

- **Settings → Actions → General → Workflow permissions:** enable *"Allow GitHub Actions to create
  and approve pull requests"* (the workflow uses the default `GITHUB_TOKEN` to open PRs).
- The scheduled trigger only fires from the workflow file on the **default branch**.

## When upstream adds new dialect syntax

1. The daily PR is labeled `needs-converter-update` and the job summary shows e.g.
   `[leftover-directive] techniques/foo.md`.
2. Add handling for the new construct in `build_references.py`, and — if it is a token that should
   never survive into prose — extend the corresponding scan in `check_references.py`.
3. Re-run `build_references.py` + `check_references.py` locally until the guard is clean.
