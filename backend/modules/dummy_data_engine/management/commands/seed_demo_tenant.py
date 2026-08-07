"""
modules/dummy_data_engine/management/commands/seed_demo_tenant.py
==================================================================
CLI entrypoint for the seed_db management command.
Source of truth: ARCHITECTURE.md §3.5

Invoked via:
  python manage.py seed_db [OPTIONS]
  python -m scripts.seed_db

Logs progress to console with rich formatting and prints the final
SeedSummaryDTO as a structured table for easy verification.
"""
from __future__ import annotations

import logging
import sys
import os

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich import box

from modules.dummy_data_engine.application.services.seed_orchestrator import (
    DemoTenantSeedOrchestrator,
)
from modules.dummy_data_engine.domain.dtos import SeedTenantRequestDTO

console = Console()


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, markup=True)],
    )
    # Suppress noisy SQLAlchemy logs unless verbose
    if not verbose:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def run_seed_command(
    tenant_id: str = "greenwood-high-001",
    student_count: int = 50,
    historical_days: int = 30,
    random_seed: int = 42,
    drop_existing: bool = False,
    verbose: bool = False,
) -> None:
    """
    Main entry point for the seed command.
    Called by manage.py seed_db and scripts/seed_db.py.
    """
    _configure_logging(verbose)
    logger = logging.getLogger(__name__)

    console.print(Panel.fit(
        "[bold blue]Smart Academic ERP -- Database Seeder[/bold blue]\n"
        f"[dim]Tenant: {tenant_id} | Students: {student_count} | Days: {historical_days}[/dim]",
        border_style="blue",
    ))

    request = SeedTenantRequestDTO(
        tenant_id=tenant_id,
        student_count=student_count,
        historical_days=historical_days,
        random_seed=random_seed,
        drop_existing=drop_existing,
    )

    try:
        orchestrator = DemoTenantSeedOrchestrator()
        summary = orchestrator.run(request)
    except Exception as exc:
        console.print(f"\n[bold red]FAILED:[/bold red] {exc}")
        logger.exception("Seed command failed")
        sys.exit(1)

    # ── Print summary table ────────────────────────────────────────────────────
    table = Table(
        title="Seed Summary",
        box=box.ROUNDED,
        border_style="green",
        show_header=True,
        header_style="bold green",
    )
    table.add_column("Entity", style="cyan", no_wrap=True)
    table.add_column("Count", style="bold white", justify="right")

    table.add_row("Class Sections",        str(summary.classes_created))
    table.add_row("Subjects",              str(summary.subjects_created))
    table.add_row("Timetable Entries",     str(summary.timetable_entries_created))
    table.add_row("Students Generated",    str(summary.students_created))
    table.add_row("Staff Generated",       str(summary.staff_created))
    table.add_row("Attendance Records",    str(summary.attendance_records_created))
    table.add_row("Fee Structures (rows)", str(summary.fee_structures_created))
    table.add_row("Fee Invoices",          str(summary.fee_invoices_created))
    table.add_row("---",                   "---")
    table.add_row(
        "[bold]Total Records[/bold]",
        f"[bold]{summary.students_created + summary.attendance_records_created + summary.fee_invoices_created:,}[/bold]",
    )
    table.add_row("Duration", f"{summary.duration_seconds:.2f}s")

    console.print()
    console.print(table)

    console.print(Panel.fit(
        f"[bold green]Seeding complete![/bold green]\n"
        f"[dim]Credentials -> {summary.seed_credentials_path}[/dim]\n\n"
        f"[yellow]Verify with:[/yellow]\n"
        f"  sqlite3 backend/db.sqlite3 \"SELECT COUNT(*) FROM students;\"\n"
        f"  sqlite3 backend/db.sqlite3 \"SELECT COUNT(*) FROM attendance_records;\"\n"
        f"  sqlite3 backend/db.sqlite3 \"SELECT COUNT(*) FROM fee_invoices;\"",
        border_style="green",
    ))

