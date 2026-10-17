import argparse
from pathlib import Path
import sys

from src.config import POC_ROOT
from src.db import article_count, initialize_database
from src.errors import PocError
from src.ingest import ingest_articles
from src.loader import load_report, seed_articles
from src.preflight import run_preflight
from src.runner import run

FRAMEWORKS = ("langchain", "langgraph", "agno")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a POC2 agent framework.")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preflight", action="store_true")
    actions.add_argument("--setup-db", action="store_true")
    actions.add_argument("--seed", action="store_true")
    actions.add_argument("--ingest", action="store_true")
    actions.add_argument("--report", type=Path)
    parser.add_argument("--framework", choices=FRAMEWORKS, default="langgraph")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.preflight:
            return 0 if run_preflight() else 1
        if args.setup_db:
            initialize_database()
            print("POC2 PostgreSQL schema and pgvector are ready.")
        elif args.seed:
            count = seed_articles()
            print(f"Seeded {count} articles. Database row count: {article_count()}.")
        elif args.ingest:
            print(f"Embedded {ingest_articles()} articles.")
        elif args.report:
            report_path = args.report
            if not report_path.is_absolute():
                report_path = POC_ROOT / report_path
            result = run(load_report(report_path), args.framework)
            print(
                f"{result.framework} run for {result.report_id}: "
                f"retries={result.retry_count}, fallback={result.used_fallback}"
            )
            print(POC_ROOT / "output" / "runs" / f"{result.report_id}_{result.framework}.json")
        return 0
    except PocError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
