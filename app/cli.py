"""CLI for Ideas Studio background tasks.

Usage:
    python -m app.cli daily
    python -m app.cli generate-ideas --project-id <id>
    python -m app.cli review --project-id <id>
"""
import argparse
import sys

from app.core.database import SessionLocal


def _should_run_pipeline_today(pipeline) -> bool:
    """Check if pipeline is enabled and today is an active day."""
    if not pipeline or not pipeline.enabled:
        return False
    if not pipeline.active_days or pipeline.active_days == "[]":
        return True
    try:
        import json
        days = json.loads(pipeline.active_days) if isinstance(pipeline.active_days, str) else pipeline.active_days
        if not days:
            return True
        from datetime import datetime
        today_name = datetime.now().strftime("%A").lower()
        return today_name in [d.lower() for d in days]
    except (json.JSONDecodeError, TypeError):
        return True


def cmd_daily(_args) -> None:
    from app.models.pipeline import ProjectPipeline
    from app.models.project import Project
    from app.services.scheduler_service import run_daily_project_tasks
    db = SessionLocal()
    try:
        projects = db.query(Project).filter(Project.status != "archived").all()
        processed = 0
        skipped = 0
        for project in projects:
            pipeline = db.query(ProjectPipeline).filter(
                ProjectPipeline.project_id == project.id
            ).first()
            if _should_run_pipeline_today(pipeline):
                result = run_daily_project_tasks(db, project.id)
                processed += 1
                ideas = result["ideas"]["generated"]
                recs = result["review"]["recommendations_created"]
                print(f"  [{project.id[:8]}] ideas={ideas}  recommendations={recs}")
            else:
                skipped += 1
        print(f"Processed {processed} project(s), {skipped} skipped (pipeline disabled or not active today).")
    finally:
        db.close()


def cmd_generate_ideas(args) -> None:
    from app.services.idea_engine import generate_idea
    from app.services.providers.llm_provider import get_llm_provider
    from app.services.providers.search_provider import get_search_provider
    from app.models.project import Project

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == args.project_id).first()
        if not project:
            print(f"Project {args.project_id} not found.")
            sys.exit(1)

        llm = get_llm_provider()
        search = get_search_provider()
        idea = generate_idea(
            db=db,
            project_id=project.id,
            project_audience=project.audience,
            project_language=project.language,
            llm=llm,
            search=search,
        )
        if idea:
            print(f"Idea created: [{idea.id[:8]}] {idea.title}")
        else:
            print("No new idea generated (possible duplicate).")
    finally:
        db.close()


def cmd_review(args) -> None:
    from app.services.optimization_engine import review_published_articles

    db = SessionLocal()
    try:
        result = review_published_articles(db, args.project_id)
        db.commit()
        print(f"Reviewed {result['articles_reviewed']} article(s).")
        print(f"  Recommendations created : {result['recommendations_created']}")
        print(f"  Notifications created   : {result['notifications_created']}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Ideas Studio background task runner",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("daily", help="Run all daily tasks for all projects")

    gen = subparsers.add_parser("generate-ideas", help="Generate ideas for a project")
    gen.add_argument("--project-id", required=True)

    rev = subparsers.add_parser("review", help="Review published articles for a project")
    rev.add_argument("--project-id", required=True)

    args = parser.parse_args()

    if args.command == "daily":
        cmd_daily(args)
    elif args.command == "generate-ideas":
        cmd_generate_ideas(args)
    elif args.command == "review":
        cmd_review(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
