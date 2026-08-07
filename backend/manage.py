#!/usr/bin/env python
"""
manage.py — CLI dispatcher for the Smart Academic ERP backend.

Usage:
    python manage.py seed_db [OPTIONS]
    python manage.py runserver
    python manage.py --help
"""
import sys
import os

# Ensure the backend/ directory is on the Python path
sys.path.insert(0, os.path.dirname(__file__))

import click
from rich.console import Console

console = Console()


@click.group()
def cli():
    """Smart Academic ERP — Management CLI."""
    pass


@cli.command("seed_db")
@click.option("--tenant", default="greenwood-high-001", show_default=True,
              help="Tenant ID to seed data for.")
@click.option("--students", default=50, show_default=True,
              help="Total number of students to generate (split evenly across sections).")
@click.option("--days", default=30, show_default=True,
              help="Number of historical attendance days to simulate.")
@click.option("--seed", default=42, show_default=True,
              help="Random seed for reproducible data generation.")
@click.option("--drop-existing", is_flag=True, default=False,
              help="Drop and recreate all tables before seeding.")
def seed_db(tenant: str, students: int, days: int, seed: int, drop_existing: bool):
    """
    Seed the database with realistic dummy data for a demo tenant.

    Runs Sub-Modules 3.1 → 3.2 → 3.3 → 3.4 → 3.5 in order.
    Equivalent to: python -m scripts.seed_db
    """
    from modules.dummy_data_engine.management.commands.seed_demo_tenant import run_seed_command
    run_seed_command(
        tenant_id=tenant,
        student_count=students,
        historical_days=days,
        random_seed=seed,
        drop_existing=drop_existing,
    )


@cli.command("runserver")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--reload", is_flag=True, default=True)
def runserver(host: str, port: int, reload: bool):
    """Start the FastAPI development server."""
    import uvicorn
    console.print(f"[bold green]Starting server at http://{host}:{port}[/bold green]")
    uvicorn.run("main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
