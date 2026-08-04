"""CLI for Ideas Studio background tasks.

Usage:
    python -m app.cli daily
    python -m app.cli generate-ideas --project-id <id>
    python -m app.cli review --project-id <id>
"""
import argparse
import sys

from sqlalchemy import select

from app.core.database import SessionLocal, set_current_project_id


def _should_run_pipeline_today(pipeline) -> bool:
    """Check if pipeline is enabled and today is an active day."""
    if not pipeline or not pipeline.is_enabled:
        return False
    schedule = pipeline.schedule or {}
    days = schedule.get("active_days") or []
    if not days:
        return True
    from datetime import datetime
    today_name = datetime.now().strftime("%A").lower()
    return today_name in [d.lower() for d in days]


def cmd_daily(_args) -> None:
    from app.models.core import Project
    from app.models.ai import Pipeline
    from app.models.reference import ProjectStatus
    from app.services.scheduler_service import run_daily_project_tasks
    db = SessionLocal()
    try:
        projects = db.execute(select(Project).where(Project.status_reason_id != ProjectStatus.ARCHIVED)).scalars().all()
        processed = 0
        skipped = 0
        for project in projects:
            set_current_project_id(project.id)
            pipeline = db.get(Pipeline, project.id)
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
        set_current_project_id(None)
        db.close()


def cmd_generate_ideas(args) -> None:
    from app.services.idea_engine import generate_idea
    from app.services.providers.llm_provider import get_llm_provider
    from app.services.providers.search_provider import get_search_provider
    from app.models.core import Project

    db = SessionLocal()
    try:
        project = db.get(Project, args.project_id)
        if not project:
            print(f"Project {args.project_id} not found.")
            sys.exit(1)
        set_current_project_id(project.id)
        profile = project.active_editorial_profile

        llm = get_llm_provider()
        search = get_search_provider()
        idea = generate_idea(
            db=db,
            project_id=project.id,
            project_audience=profile.audience if profile else None,
            project_language=project.locale.split("-")[0] if project.locale else "fr",
            llm=llm,
            search=search,
        )
        if idea:
            title = idea.current_revision.title if idea.current_revision else ""
            print(f"Idea created: [{idea.id[:8]}] {title}")
        else:
            print("No new idea generated (possible duplicate).")
    finally:
        set_current_project_id(None)
        db.close()


def cmd_review(args) -> None:
    from app.services.optimization_engine import review_published_articles

    db = SessionLocal()
    set_current_project_id(args.project_id)
    try:
        result = review_published_articles(db, args.project_id)
        db.commit()
        print(f"Reviewed {result['articles_reviewed']} article(s).")
        print(f"  Recommendations created : {result['recommendations_created']}")
        print(f"  Notifications created   : {result['notifications_created']}")
    finally:
        set_current_project_id(None)
        db.close()


def cmd_worker(_args) -> None:
    """Start the background worker (scheduler)."""
    from app.services.worker import start_scheduler, stop_scheduler
    import time
    print("Starting Ideas Studio worker...")
    start_scheduler()
    print("Worker started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()
        print("Worker stopped.")


def cmd_scheduler(_args) -> None:
    """Run all scheduled tasks once (for cron-based scheduling)."""
    from app.services.worker import check_scheduled_publications, run_daily_tasks, run_pipelines
    print("Running scheduled tasks...")
    check_scheduled_publications()
    run_daily_tasks()
    run_pipelines()
    print("Scheduled tasks completed.")


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

    subparsers.add_parser("worker", help="Start the background scheduler worker")
    subparsers.add_parser("scheduler", help="Run all scheduled tasks once")

    args = parser.parse_args()

    if args.command == "daily":
        cmd_daily(args)
    elif args.command == "generate-ideas":
        cmd_generate_ideas(args)
    elif args.command == "review":
        cmd_review(args)
    elif args.command == "worker":
        cmd_worker(args)
    elif args.command == "scheduler":
        cmd_scheduler(args)
    else:
        parser.print_help()
        sys.exit(1)


# Aliases for worker.py entry point
run_worker = cmd_worker
run_scheduler = cmd_scheduler

if __name__ == "__main__":
    main()
