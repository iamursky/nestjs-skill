#!/usr/bin/env python3
"""Build the nestjs-skill reference bundle from a checkout of the upstream
nestjs/docs.nestjs.com repository.

NestJS's documentation lives in a dedicated Angular docs site whose prose pages
are authored as Markdown under `content/` in a small custom dialect: code fences
carry `@@filename(...)` / `@@switch` directives that the site renders as a
TypeScript/JavaScript tab toggle, callouts are `> info **Hint**` blockquotes,
images are `<figure><img src="/assets/...">`, and `<app-banner-*>` Angular tags
inject promo cards. This script converts that material into clean, faithful
Markdown, mirrors the `content/` tree under `references/`, regenerates
CONTENTS.md (grouped in the site's sidebar order), and copies the upstream
LICENSE.

Conversion choices (documented so a future sync is predictable):
  * `@@filename(name)` / `@@switch` — keep the **TypeScript** variant (NestJS's
    canonical language), drop the `@@switch` JavaScript half, and surface the
    filename as a `title="name.ts"` info-string on the fence. Empty
    `@@filename()` -> no title.
  * `> info/warning/error/warn **Label**` callouts are already valid Markdown
    blockquotes and are kept verbatim.
  * `<app-banner-*>` promo tags are stripped.
  * `<figure><img src="/assets/x">` -> `![](https://docs.nestjs.com/assets/x)`.
  * Root-relative links (`/techniques/...`, `href="/..."`, `routerLink="/..."`)
    -> absolute `https://docs.nestjs.com/...` (the live site resolves slugs).
  * Mustache brace escapes `{{ '{' }}` / `{{ '}' }}` and `&#123;`/`&#125;` ->
    literal `{` / `}`.
  * Headings start at H3 on the site; every heading is promoted by two levels
    (`### -> #`) so each page has exactly one H1.
  * Raw HTML (tables, <details>, file-tree divs) is left intact — GFM renders it.

Deterministic and stdlib-only (no third-party dependencies), so it can run
unattended in CI to keep the bundle in sync with the upstream docs.

Usage:
    python3 tools/build_references.py --docs-repo <path-to-docs.nestjs.com> \
            --out skills/nestjs/references
"""
import argparse, os, re, posixpath, shutil

GH = "https://github.com/nestjs/docs.nestjs.com"
BRANCH = "master"
CONTENT = "content"            # docs prose lives under content/
SITE = "https://docs.nestjs.com"


# ---------------------------------------------------------------------------
# Code fences: rewrite @@filename / @@switch, then stash so prose passes never
# touch fenced code (examples contain `#` comments, `<Generic>` types, links…).
# ---------------------------------------------------------------------------
FENCE_RE = re.compile(r"^(?P<fence>```)(?P<info>[^\n]*)\n(?P<body>.*?)^```[ \t]*$",
                      re.DOTALL | re.M)
FILENAME_RE = re.compile(r"^@@filename\((?P<name>[^)]*)\)[ \t]*$", re.M)


def transform_fence(m):
    info = m.group("info").strip()
    body = m.group("body")
    lang = info.split()[0] if info else ""

    # Extract and drop the @@filename(...) directive line, remembering the name.
    name = None
    fn = FILENAME_RE.search(body)
    if fn:
        name = fn.group("name").strip()
        body = FILENAME_RE.sub("", body, count=1)

    # @@switch splits TS (above) from JS (below) — keep only the TS half.
    parts = re.split(r"^@@switch[ \t]*$", body, maxsplit=1, flags=re.M)
    body = parts[0]

    body = body.strip("\n")
    # If the directive left a leading blank line (e.g. `@@filename(main)\n\n…`),
    # body.strip already removed it.

    new_info = info
    if name:
        new_info = "%s title=\"%s.ts\"" % (lang or "typescript", name)
    return "```%s\n%s\n```" % (new_info, body)


def rewrite_and_stash_fences(text):
    blocks = []

    def repl(m):
        blocks.append(transform_fence(m))
        return "\x00FENCE%d\x00" % (len(blocks) - 1)

    text = FENCE_RE.sub(repl, text)
    return text, blocks


def restore_fences(text, blocks):
    return re.sub(r"\x00FENCE(\d+)\x00", lambda m: blocks[int(m.group(1))], text)


# ---------------------------------------------------------------------------
# Prose transforms (run with fences stashed out).
# ---------------------------------------------------------------------------
def strip_banners(text):
    # <app-banner-foo></app-banner-foo> or self-closing <app-banner-foo />
    text = re.sub(r"<app-banner[\w-]*\b[^>]*>\s*</app-banner[\w-]*>", "", text)
    text = re.sub(r"<app-banner[\w-]*\b[^>]*/>", "", text)
    return text


def convert_figures(text):
    def repl(m):
        src = m.group("src").strip()
        if src.startswith("/"):
            src = SITE + src
        return "![](%s)" % src

    return re.sub(
        r"<figure\b[^>]*>\s*<img\b[^>]*?\bsrc=\"(?P<src>[^\"]+)\"[^>]*?/?>\s*</figure>",
        repl, text, flags=re.DOTALL)


def unescape_braces(text):
    # Angular text-interpolation escapes: `{{ 'literal' }}` / `{{ "literal" }}`
    # emit the quoted literal verbatim on the site (used to show `{`, `}`, `}}`,
    # `${{ … }}`, handlebars `{{ x }}`, etc. without Angular interpreting them).
    # Recover the literal everywhere — prose *and* code fences — unescaping any
    # `\{` / `\}` inside it. These are the only `{{ '…' }}`/`{{ "…" }}` forms in
    # the corpus, so a blanket pass is faithful.
    def lit(m):
        return m.group(1).replace("\\}", "}").replace("\\{", "{")

    text = re.sub(r"\{\{\s*'([^']*)'\s*\}\}", lit, text)
    text = re.sub(r"\{\{\s*\"([^\"]*)\"\s*\}\}", lit, text)
    # backslash-escaped `${…}` (shell / GitHub Actions vars escaped for the renderer)
    text = text.replace("\\${", "${")
    # stray HTML entities for braces
    text = text.replace("&#123;", "{").replace("&#125;", "}")
    return text


def _abs_site(target):
    """Turn a docs-relative link target into an absolute docs.nestjs.com URL.

    The site routes every doc-relative link from the site root regardless of how
    it's written, so bare (`middleware`), explicitly-relative (`./faq/x`,
    `../security/y`) and root-relative (`/guards`) targets all collapse to a
    leading-slash slug. External (`http(s)://`, `mailto:`) and pure-anchor
    (`#...`) targets are left untouched. Returns None when unchanged.
    """
    t = target.strip()
    if not t or t.startswith(("http://", "https://", "mailto:", "#", SITE)):
        return None
    t = re.sub(r"^(?:\.\.?/)+", "", t)             # drop leading ./ and ../
    if not t.startswith("/"):
        t = "/" + t
    return SITE + t


def rewrite_links(text):
    # markdown [label](target) and ![alt](src) -> absolute site URL
    def md(m):
        url = _abs_site(m.group(2))
        return m.group(0) if url is None else "[%s](%s)" % (m.group(1), url)

    text = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", md, text)
    # html routerLink="x" -> href="x", then any doc-relative href -> absolute
    text = re.sub(r'routerLink="([^"]*)"', r'href="\1"', text)

    def href(m):
        url = _abs_site(m.group(1))
        return m.group(0) if url is None else 'href="%s"' % url

    text = re.sub(r'href="([^"]*)"', href, text)
    return text


def promote_headings(text):
    def repl(m):
        level = len(m.group(1))
        return "#" * max(1, level - 2) + " "

    return re.sub(r"^(#{1,6})\s+", repl, text, flags=re.M)


# ---------------------------------------------------------------------------
# Conversion entry point.
# ---------------------------------------------------------------------------
def humanize(slug):
    words = [w for w in re.split(r"[-_/]", slug) if w]
    return " ".join(w[:1].upper() + w[1:] for w in words) or slug


def convert(path, src_rel, slug):
    raw = open(path, encoding="utf-8").read()
    raw = unescape_braces(raw)          # whole-text: escapes live in prose *and* code

    text, fences = rewrite_and_stash_fences(raw)
    text = strip_banners(text)
    text = convert_figures(text)
    text = rewrite_links(text)
    text = promote_headings(text)

    text = restore_fences(text, fences)

    # Tidy whitespace.
    text = re.sub(r"[ \t]+$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    # Guarantee a single leading H1.
    if not re.search(r"^# ", text, re.M):
        text = "# %s\n\n%s" % (humanize(slug), text)

    return "> Source: %s/blob/%s/%s/%s\n\n%s" % (GH, BRANCH, CONTENT, src_rel, text)


# ---------------------------------------------------------------------------
# CONTENTS.md — grouped in the docs-site sidebar order.
# Curated structure mapping each sidebar section to actual content/ file paths.
# Files present in the bundle but absent here fall through to "Other pages".
# ---------------------------------------------------------------------------
SECTIONS = [
    ("Introduction", ["introduction"]),
    ("Overview", [
        "first-steps", "controllers", "components", "modules", "middlewares",
        "exception-filters", "pipes", "guards", "interceptors", "custom-decorators",
    ]),
    ("Fundamentals", [
        "fundamentals/dependency-injection", "fundamentals/async-components",
        "fundamentals/dynamic-modules", "fundamentals/provider-scopes",
        "fundamentals/circular-dependency", "fundamentals/module-reference",
        "fundamentals/lazy-loading-modules", "fundamentals/execution-context",
        "fundamentals/lifecycle-events", "fundamentals/discovery-service",
        "fundamentals/platform-agnosticism", "fundamentals/unit-testing",
    ]),
    ("Techniques", [
        "techniques/configuration", "techniques/sql", "techniques/mongo",
        "techniques/validation", "techniques/caching", "techniques/serialization",
        "techniques/versioning", "techniques/task-scheduling", "techniques/queues",
        "techniques/logger", "techniques/cookies", "techniques/events",
        "techniques/compression", "techniques/file-upload", "techniques/streaming-files",
        "techniques/http-module", "techniques/sessions", "techniques/mvc",
        "techniques/performance", "techniques/server-sent-events",
    ]),
    ("Security", [
        "security/authentication", "security/authorization",
        "security/encryption-hashing", "security/helmet", "security/cors",
        "security/csrf", "security/rate-limiting",
    ]),
    ("GraphQL", [
        "graphql/quick-start", "graphql/resolvers-map", "graphql/mutations",
        "graphql/subscriptions", "graphql/scalars", "graphql/directives",
        "graphql/interfaces", "graphql/unions-and-enums", "graphql/field-middleware",
        "graphql/mapped-types", "graphql/plugins", "graphql/complexity",
        "graphql/extensions", "graphql/cli-plugin", "graphql/schema-generator",
        "graphql/sharing-models", "graphql/guards-interceptors", "graphql/federation",
    ]),
    ("WebSockets", [
        "websockets/gateways", "websockets/exception-filters", "websockets/pipes",
        "websockets/guards", "websockets/interceptors", "websockets/adapter",
    ]),
    ("Microservices", [
        "microservices/basics", "microservices/redis", "microservices/mqtt",
        "microservices/nats", "microservices/rabbitmq", "microservices/kafka",
        "microservices/grpc", "microservices/custom-transport",
        "microservices/exception-filters", "microservices/pipes",
        "microservices/guards", "microservices/interceptors",
    ]),
    ("Deployment", ["deployment"]),
    ("Standalone applications", ["application-context"]),
    ("CLI", [
        "cli/overview", "cli/workspaces", "cli/libraries", "cli/usages", "cli/scripts",
    ]),
    ("OpenAPI", [
        "openapi/introduction", "openapi/types-and-parameters", "openapi/operations",
        "openapi/security", "openapi/mapped-types", "openapi/decorators",
        "openapi/cli-plugin", "openapi/other-features",
    ]),
    ("Recipes", [
        "recipes/repl", "recipes/crud-generator", "recipes/swc", "recipes/passport",
        "recipes/hot-reload", "recipes/mikroorm", "recipes/sql-typeorm",
        "recipes/mongodb", "recipes/sql-sequelize", "recipes/router-module",
        "recipes/documentation", "recipes/cqrs", "recipes/prisma", "recipes/sentry",
        "recipes/serve-static", "recipes/nest-commander", "recipes/async-local-storage",
        "recipes/necord", "recipes/suites", "recipes/terminus",
    ]),
    ("FAQ", [
        "faq/serverless", "faq/http-adapter", "faq/keep-alive-connections",
        "faq/global-prefix", "faq/raw-body", "faq/hybrid-application",
        "faq/multiple-servers", "faq/request-lifecycle", "faq/errors",
    ]),
    ("Devtools", ["devtools/overview", "devtools/ci-cd"]),
    ("Migration guide", ["migration"]),
    ("Discover & support", ["discover/who-uses", "enterprise", "support"]),
]


def first_h1(path):
    for line in open(path, encoding="utf-8"):
        m = re.match(r"#\s+(.+)", line)
        if m:
            return m.group(1).strip()
    return os.path.basename(path)


def write_index(out_root, slugs):
    remaining = set(slugs)
    total = len(slugs)
    lines = [
        "# NestJS documentation — reference index", "",
        "Faithful Markdown conversion of the official NestJS documentation "
        "(%s), generated from the [nestjs/docs.nestjs.com](%s) `content/` source "
        "by `tools/build_references.py`. Each file keeps a `> Source:` link to its "
        "upstream file on GitHub. See `LICENSE` (MIT, Kamil Myśliwiec)." % (SITE, GH), "",
        "Targets **NestJS v11**. **%d pages.**" % total, "",
    ]

    def entry(slug):
        rel = slug + ".md"
        title = first_h1(os.path.join(out_root, rel))
        return "- [%s](%s) — `%s`" % (title, rel, rel)

    for label, members in SECTIONS:
        present = [s for s in members if s in remaining]
        if not present:
            continue
        lines += ["## " + label, ""]
        for s in present:
            lines.append(entry(s))
            remaining.discard(s)
        lines.append("")

    if remaining:
        lines += ["## Other pages", ""]
        for s in sorted(remaining):
            lines.append(entry(s))
        lines.append("")

    open(os.path.join(out_root, "CONTENTS.md"), "w", encoding="utf-8").write(
        "\n".join(lines) + "\n")


def write_license(repo, out_root):
    note = (
        "The reference material in this directory is derived from the official NestJS\n"
        "documentation (https://github.com/nestjs/docs.nestjs.com), converted from its\n"
        "custom Markdown source to plain Markdown. It is redistributed here under the\n"
        "original MIT license, reproduced verbatim below.\n\n"
        "--------------------------------------------------------------------------------\n\n"
    )
    up = os.path.join(repo, "LICENSE")
    text = open(up, encoding="utf-8").read() if os.path.isfile(up) else ""
    open(os.path.join(out_root, "LICENSE"), "w", encoding="utf-8").write(note + text)


# ---------------------------------------------------------------------------
# Build.
# ---------------------------------------------------------------------------
def build(repo, out_root):
    src_root = os.path.join(repo, CONTENT)
    if not os.path.isdir(src_root):
        raise SystemExit("error: %s has no %s/ directory" % (repo, CONTENT))

    if os.path.isdir(out_root):
        shutil.rmtree(out_root)
    os.makedirs(out_root)

    slugs = []
    for dp, _, files in os.walk(src_root):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dp, fn)
            src_rel = os.path.relpath(full, src_root).replace(os.sep, "/")
            slug = src_rel[:-len(".md")]
            md = convert(full, src_rel, slug)
            dest = os.path.join(out_root, slug + ".md")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "w", encoding="utf-8").write(md)
            slugs.append(slug)

    write_index(out_root, sorted(slugs))
    write_license(repo, out_root)
    return len(slugs)


def main():
    ap = argparse.ArgumentParser(
        description="Build the nestjs-skill reference bundle from a docs.nestjs.com checkout.")
    ap.add_argument("--docs-repo", required=True,
                    help="Path to a checkout of nestjs/docs.nestjs.com")
    ap.add_argument("--out", required=True,
                    help="Output references directory (rebuilt from scratch)")
    args = ap.parse_args()
    n = build(args.docs_repo, args.out)
    print("Built %d reference pages -> %s" % (n, args.out))


if __name__ == "__main__":
    main()
