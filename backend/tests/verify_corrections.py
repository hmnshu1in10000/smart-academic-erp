"""Quick backend verification script for correction.md Section 5 steps 1-3."""
import sys, datetime

# Step 1a: JWT TokenPayload with assigned_sections
from shared_kernel.auth.jwt_utils import TokenPayload, create_access_token
t = TokenPayload(
    sub='a@b.com', tenant_id='t1', role='teacher',
    exp=datetime.datetime.now(datetime.timezone.utc),
    assigned_sections=('10-A',)
)
assert t.assigned_sections == ('10-A',), f"FAIL: {t.assigned_sections}"
print("PASS Step1a: TokenPayload assigned_sections carries teacher scope")

# Step 1b: Token creation embeds sections
tok = create_access_token('a@b.com', 't1', 'teacher', assigned_sections=['10-A'])
assert isinstance(tok, str) and len(tok) > 20
print("PASS Step1b: create_access_token accepts assigned_sections")

# Step 2a: DTOs with template fields
from modules.ai_analytics.domain.dtos import GeneratedSQLDTO, NLQueryRequestDTO, ChatTurnDTO
dto = GeneratedSQLDTO(
    raw_query='q', sql='SELECT 1', explanation='e', confidence_score=0.95,
    single_result_template='Found {total_active} active students.',
    multi_result_template='Found {row_count} results.',
    zero_result_template='No records found.'
)
assert dto.single_result_template == 'Found {total_active} active students.'
print("PASS Step2a: GeneratedSQLDTO template fields OK")

req = NLQueryRequestDTO(query='test', tenant_id='t1', debug_mode=True)
assert req.debug_mode is True
print("PASS Step2a: NLQueryRequestDTO debug_mode field OK")

# Step 1c: GuardedQueryExecutor hardened RBAC
from modules.ai_analytics.application.services.guarded_executor import GuardedQueryExecutor, SecurityViolationError
ex = GuardedQueryExecutor()

# DDL blocked for admin
ddl = "DROP TABLE students"
try:
    ex.validate_sql(ddl, 'tid', 'ADMIN', '')
    print("FAIL: DDL not blocked")
    sys.exit(1)
except SecurityViolationError:
    print("PASS Step1c: DDL blocked for admin")

# Parent without identity predicate → rejected
no_pred = "SELECT full_name FROM students WHERE students.tenant_id = 'tid' LIMIT 10"
try:
    ex.validate_sql(no_pred, 'tid', 'PARENT', 'parent@demo.school')
    print("FAIL: Missing identity predicate should be blocked")
    sys.exit(1)
except SecurityViolationError as e:
    print("PASS Step1c: Missing identity predicate blocked:", str(e)[:70])

# Parent with correct identity predicate in subquery → accepted
good_parent = (
    "SELECT s.full_name AS student_name FROM students s "
    "WHERE s.tenant_id = 'tid' "
    "AND s.id IN (SELECT id FROM students WHERE guardian_user_id = 'parent@demo.school') LIMIT 10"
)
try:
    validated = ex.validate_sql(good_parent, 'tid', 'PARENT', 'parent@demo.school')
    print("PASS Step1c: Valid parent SQL with subquery accepted")
except SecurityViolationError as e:
    print("FAIL: Valid parent SQL rejected:", e)
    sys.exit(1)

# Admin bypasses identity predicate check
admin_sql = "SELECT COUNT(id) AS total FROM students WHERE tenant_id = 'tid' LIMIT 10"
try:
    ex.validate_sql(admin_sql, 'tid', 'ADMIN', '')
    print("PASS Step1c: Admin SQL accepted without identity predicate")
except SecurityViolationError as e:
    print("FAIL: Admin SQL rejected:", e)
    sys.exit(1)

# Step 3: Facade import chain
from modules.ai_analytics.application.services.analytics_facade import ConversationalAnalyticsFacade
fac = ConversationalAnalyticsFacade()
print("PASS Step3: ConversationalAnalyticsFacade import OK")

from modules.ai_analytics.api.views import router as ai_router
print("PASS Step3: ai_analytics views import OK")

# Step 3b: Local interpolation (_interpolate_summary)
from modules.ai_analytics.domain.dtos import QueryExecutionResultDTO
gen_dto = GeneratedSQLDTO(
    raw_query='active students', sql='SELECT 1', explanation='e',
    single_result_template='There are {total_active} active students enrolled.',
    multi_result_template='Found {row_count} records.',
    zero_result_template='No records.'
)
exec_dto = QueryExecutionResultDTO(
    executed_sql='SELECT 1', columns=('total_active',), rows=((120,),),
    row_count=1, execution_time_ms=5.0, error=None
)
summary = fac._interpolate_summary(gen_dto, exec_dto)
assert summary == 'There are 120 active students enrolled.', f"Got: {summary}"
print("PASS Step3b: Local interpolation produces:", summary)

print()
print("=" * 50)
print("ALL BACKEND STEPS 1-3 VERIFIED")
print("=" * 50)
