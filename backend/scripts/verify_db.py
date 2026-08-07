import sys
sys.path.insert(0, 'backend')

from modules.dummy_data_engine.infrastructure.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    tables = ['class_sections','students','attendance_records','fee_structures','fee_invoices']
    print('=== DATABASE VERIFICATION ===')
    for t in tables:
        count = conn.execute(text('SELECT COUNT(*) FROM ' + t)).scalar()
        print('  {:30s}: {:>6}'.format(t, count))

    print()
    print('=== ATTENDANCE STATUS BREAKDOWN ===')
    for status, label in [('P','Present'),('A','Absent'),('L','Late')]:
        n = conn.execute(text("SELECT COUNT(*) FROM attendance_records WHERE status='" + status + "'")).scalar()
        print('  {:10s}: {:>6}'.format(label, n))

    print()
    print('=== FEE INVOICE STATUS BREAKDOWN ===')
    for s in ['PAID','PENDING','OVERDUE','PARTIAL']:
        n = conn.execute(text("SELECT COUNT(*) FROM fee_invoices WHERE status='" + s + "'")).scalar()
        print('  {:10s}: {:>6}'.format(s, n))

    print()
    print('=== SAMPLE STUDENTS ===')
    rows = conn.execute(text('SELECT roll_number, full_name, guardian_name, guardian_phone FROM students ORDER BY roll_number LIMIT 5')).fetchall()
    for r in rows:
        print('  Roll {:02d}: {:30s} Parent: {}'.format(r[0], r[1], r[2]))

    print()
    print('=== CLASS SECTIONS ===')
    rows = conn.execute(text('SELECT display_name, grade_level, room_number FROM class_sections')).fetchall()
    for r in rows:
        print('  {} (Grade {}, Room {})'.format(r[0], r[1], r[2]))
