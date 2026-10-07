"""Command line entry point.

  python -m integration_agent profile --partner Shopify --url https://shopify.dev/docs/api/admin-rest
  python -m integration_agent profile --partner Acme --file acme_docs.txt
  python -m integration_agent backlog examples/backlog.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backlog import load_backlog, load_profiles, metrics, prioritize, slug
from .extract import extract_profile
from .fetch import fetch_docs

PROFILES_DIR = Path("profiles")


def cmd_profile(args) -> None:
    if args.file:
        docs_text = Path(args.file).read_text()
        docs_url = args.url or f"file:{args.file}"
    else:
        docs_text = fetch_docs(args.url)
        docs_url = args.url
    profile = extract_profile(args.partner, docs_url, docs_text)
    PROFILES_DIR.mkdir(exist_ok=True)
    out = PROFILES_DIR / f"{slug(profile.partner)}.json"
    out.write_text(profile.model_dump_json(indent=2))
    print(f"Saved {out}")
    print(f"  auth: {profile.auth.type.value} | endpoints: {len(profile.key_endpoints)} | "
          f"sandbox: {profile.sandbox.available} | partner program: {profile.partner_program.required}")
    for q in profile.open_questions:
        print(f"  open question: {q}")


def cmd_backlog(args) -> None:
    items = load_backlog(args.csv)
    profiles = load_profiles(PROFILES_DIR) if PROFILES_DIR.exists() else {}
    print(f"{'#':>2}  {'Partner':<22}{'Score':>7}  Status")
    for n, (item, score, prof) in enumerate(prioritize(items, profiles), 1):
        status = "no profile yet" if prof is None else (
            "BUILD READY" if prof.build_ready else f"access: {prof.access_status.value}")
        print(f"{n:>2}  {item.partner:<22}{score:>7}  {status}")
    print("\nMetrics:", json.dumps(metrics(items, profiles), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="integration_agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("profile", help="Build an integration profile from API docs")
    p.add_argument("--partner", required=True)
    p.add_argument("--url", help="Docs URL to fetch")
    p.add_argument("--file", help="Local docs file instead of fetching")
    p.set_defaults(func=cmd_profile)

    b = sub.add_parser("backlog", help="Rank the integration backlog and show metrics")
    b.add_argument("csv")
    b.set_defaults(func=cmd_backlog)

    args = parser.parse_args()
    if args.cmd == "profile" and not (args.url or args.file):
        parser.error("profile needs --url or --file")
    args.func(args)


if __name__ == "__main__":
    main()
