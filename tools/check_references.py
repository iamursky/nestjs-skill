#!/usr/bin/env python3
"""Guard for the generated reference bundle. Catches conversion defects so an
automated docs sync never silently ships broken Markdown — most importantly,
leftover NestJS doc-dialect tokens that `build_references.py` should have
consumed (a signal the converter needs updating for new upstream syntax).

Checks: empty/tiny files, missing H1, unbalanced code fences, broken
intra-bundle links, and leftover dialect tokens outside code — `@@filename` /
`@@switch` directives, `<app-banner-*>` promo tags, and `{{ '{' }}` mustache
brace escapes.

Note: NestJS prose and examples legitimately contain `#` comments, `<Generic>`
TypeScript types and HTML tables inside ```code fences; those are stripped
before the dialect scan so they never trip the guard.

Exit code 0 = clean, 1 = issues found (printed). Stdlib only.

Usage: python3 tools/check_references.py <references-dir>
"""
import os, re, sys


def strip_code(text):
    text = re.sub(r"^```.*?^```", "", text, flags=re.DOTALL | re.M)
    text = re.sub(r"`[^`\n]*`", "", text)          # inline code spans
    return text


def main():
    if len(sys.argv) != 2:
        print("usage: check_references.py <references-dir>", file=sys.stderr)
        return 2
    root = sys.argv[1]
    mds = [os.path.join(dp, f) for dp, _, fs in os.walk(root)
           for f in fs if f.endswith(".md")]
    issues = []

    def add(kind, path, detail=""):
        issues.append((kind, os.path.relpath(path, root), detail))

    for m in mds:
        base = os.path.basename(m)
        text = open(m, encoding="utf-8").read()
        if base not in ("CONTENTS.md", "LICENSE"):
            if len(text) < 120:
                add("empty/tiny", m)
            if not re.search(r"^# ", text, re.M):
                add("missing-H1", m)
        if len(re.findall(r"^```", text, re.M)) % 2:
            add("unbalanced-fences", m)

        nocode = strip_code(text)
        # leftover dialect tokens the converter should have consumed
        if re.search(r"@@(filename|switch)\b", nocode):
            add("leftover-directive", m)
        if re.search(r"<app-banner", nocode):
            add("leftover-banner", m)
        # Angular interpolation escapes (`{{ '…' }}` / `{{ "…" }}`) and backslash-
        # escaped `${…}` live inside code fences too, so scan the FULL text.
        if re.search(r"\{\{\s*['\"]", text):
            add("leftover-mustache", m)
        if "\\${" in text:
            add("leftover-escape", m)

        # broken intra-bundle links (relative, not http/anchor/mailto)
        d = os.path.dirname(m)
        for tgt in re.findall(r"\]\(([^)]+)\)", text):
            t = tgt.split("#", 1)[0]
            if not t or t.startswith(("http", "mailto:")):
                continue
            p = (root + t) if t.startswith("/") else os.path.normpath(os.path.join(d, t))
            if not os.path.exists(p):
                add("broken-link", m, tgt)

    if not issues:
        n = len([m for m in mds if os.path.basename(m) != "CONTENTS.md"])
        print("OK: %d pages, no issues." % n)
        return 0
    print("FOUND %d issue(s):" % len(issues))
    for kind, path, detail in issues:
        print("  [%s] %s%s" % (kind, path, (" :: " + detail) if detail else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
