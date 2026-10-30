import argparse
from pathlib import Path
import sys

from src.config import POC_ROOT, resolve_report_path
from src.db import article_count, initialize_database
from src.errors import PocError
from src.ingest import ingest_articles
from src.pipeline import load_report, run_recommendation, save_result
from src.preflight import run_preflight
from src.vendor_loader import seed_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the health RAG POC.")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preflight", action="store_true", help="Check Codespaces prerequisites.")
    actions.add_argument("--setup-db", action="store_true", help="Create the database schema.")
    actions.add_argument("--seed", action="store_true", help="Load the 33-article snapshot.")
    actions.add_argument("--ingest", action="store_true", help="Embed all seeded articles.")
    actions.add_argument("--report", type=Path, help="Run the pipeline for a report JSON file.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.preflight:
            return 0 if run_preflight() else 1
        if args.setup_db:
            initialize_database()
        elif args.seed:
            count = seed_database()
            print(f"Loaded {count} articles. Database row count: {article_count()}.")
        elif args.ingest:
            count = ingest_articles()
            print(f"Added embeddings to {count} articles.")
        elif args.report:
            report_path = resolve_report_path(args.report)
            result = run_recommendation(load_report(report_path))
            output_path = save_result(result)
            print(f"Recommendation run completed: {output_path}")
        return 0
    except PocError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
