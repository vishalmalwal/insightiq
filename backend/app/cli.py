"""InsightIQ developer CLI. `insightiq seed` loads the sample datasets into both stores."""
from __future__ import annotations

import argparse

from app.core.logging import configure_logging, get_logger

__version__ = "0.1.0"


def _seed() -> None:
    from app.db.session import SessionLocal, create_all
    from app.services.sample_data.seed import seed_sample_data

    create_all()  # dev convenience; prod uses `alembic upgrade head`
    log = get_logger("insightiq.cli")
    with SessionLocal() as session:
        projects = seed_sample_data(session)
    log.info("seed_complete", projects=[p.slug for p in projects])
    print("Seeded projects:", ", ".join(p.slug for p in projects))


def _git_sha() -> str | None:
    import subprocess

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:  # noqa: BLE001 - git optional
        return None


def _eval(ci: bool, threshold: float, provider: str | None) -> None:
    import asyncio
    import os
    import sys

    if provider:
        os.environ["LLM_PROVIDER"] = provider
        from app.core.config import get_settings

        get_settings.cache_clear()  # pick up the overridden provider

    from app.db.session import SessionLocal, create_all
    from app.services.eval.harness import run_suite
    from app.services.sample_data.seed import seed_sample_data

    create_all()
    with SessionLocal() as session:
        seed_sample_data(session)  # idempotent — ensure the sample data is present
        summary = asyncio.run(run_suite(session, git_sha=_git_sha()))

    print(f"\nEval suite {summary.suite_version} — {summary.n_cases} cases ({summary.provider})")
    print(f"  execution accuracy : {summary.exec_accuracy:.0%}")
    print(f"  valid-SQL rate     : {summary.valid_sql_rate:.0%}")
    print(f"  intent accuracy    : {summary.intent_accuracy:.0%}")
    print(f"  avg latency        : {summary.avg_latency_ms:.0f} ms")
    print(f"  total cost         : ${summary.total_cost_usd:.4f}")

    if ci and summary.exec_accuracy < threshold:
        print(f"\nFAIL: execution accuracy {summary.exec_accuracy:.0%} < {threshold:.0%}")
        sys.exit(1)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(prog="insightiq", description="InsightIQ developer CLI")
    # Conventional flag alias for the `version` subcommand.
    parser.add_argument(
        "--version", action="version", version=f"insightiq {__version__}"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("version", help="Print version")
    sub.add_parser("seed", help="Load sample datasets + create sample projects")
    ev = sub.add_parser("eval", help="Run the SQL-accuracy eval suite")
    ev.add_argument("--ci", action="store_true", help="Exit non-zero if below --threshold")
    ev.add_argument("--threshold", type=float, default=0.75, help="Min execution accuracy")
    ev.add_argument("--provider", choices=["mock", "gemini", "anthropic"], default=None,
                    help="Score a specific LLM provider (default: configured provider)")
    args = parser.parse_args()

    if args.command == "version":
        print(f"insightiq {__version__}")
    elif args.command == "seed":
        _seed()
    elif args.command == "eval":
        _eval(ci=args.ci, threshold=args.threshold, provider=args.provider)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
