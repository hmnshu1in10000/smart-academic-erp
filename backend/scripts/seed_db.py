"""scripts/seed_db.py — Alternate entry point for `python -m scripts.seed_db`"""
import sys
import os

# Add backend/ to path so all imports resolve correctly
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import click
from modules.dummy_data_engine.management.commands.seed_demo_tenant import run_seed_command


@click.command()
@click.option("--tenant", default="greenwood-high-001", show_default=True)
@click.option("--students", default=50, show_default=True)
@click.option("--days", default=30, show_default=True)
@click.option("--seed", default=42, show_default=True)
@click.option("--drop-existing", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
def main(tenant, students, days, seed, drop_existing, verbose):
    """Seed the ERP database with realistic dummy data."""
    run_seed_command(
        tenant_id=tenant,
        student_count=students,
        historical_days=days,
        random_seed=seed,
        drop_existing=drop_existing,
        verbose=verbose,
    )


if __name__ == "__main__":
    main()
