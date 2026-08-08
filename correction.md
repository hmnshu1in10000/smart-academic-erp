# System Correction & Feature Enhancement Specification (`correction.md`)

**Project:** AI-Powered Academic ERP (FastAPI + SQLite/PostgreSQL + React 19/Tailwind CSS v4 + React Native Expo)
**Prepared for:** IDE Agent (Google Antigravity) — sequential execution
**Source:** Codebase security & functionality review, `smart-academic-erp/`
**Status:** Mandatory — do not deploy to any non-demo environment until all sections are implemented and the verification checklist in Section 5 passes.

---

## Preface — Why this document exists

The current build has three classes of problems, all confirmed by direct code inspection:

1. **Data isolation is broken.** `GET /students`, `GET /attendance/summary`, `GET /fees/summary` filter only by `tenant_id`, never by requesting user. `/parent/child-summary` and `/student/academic-summary` resolve "my child" / "myself" via `.first()` on the tenant's student table — i.e. every parent and every student currently sees the **same, arbitrary, first-in-table** student record. The AI analytics RBAC (`guarded_executor.py`) only verifies the substring `tenant_id` appears in generated SQL; it never inspects whether the parent/student subquery predicate is actually present, so the entire cross-family isolation guarantee is currently enforced by *prompt wording only*, which an LLM can silently drop.
2. **The web dashboard has no role model.** `App.tsx` and `Sidebar.tsx` route every authenticated role — admin, principal, teacher, student, parent — into the identical admin views. Teacher has zero dedicated screens. Student/parent get only cosmetic label swaps on the admin dashboard, not actually restricted data or navigation.
3. **The AI chat has no transparency controls and re-sends raw data unnecessarily.** There is no way to inspect generated SQL from the UI, and the answer-composition path has no formal contract for local (non-LLM) interpolation of results into natural language.

This document is the complete fix specification. It assumes the codebase state described in the review (module layout under `backend/modules/`, `web-dashboard/src/`, `mobile-app/src/`) and gives literal file paths, complete schemas, and complete logic — no placeholders.

---

## Section 1: Security, JWT Scoping & Hardened RBAC Specification

### 1.1 JWT payload extension — carry role-scope claims, not just role name

`backend/shared_kernel/auth/jwt_utils.py` — `TokenPayload` currently carries `sub`, `tenant_id`, `role`, `exp`. This is insufficient to scope a **teacher** to their assigned section(s) without a second DB round-trip on every request. Extend the token payload and the login issuer:

```python
# backend/shared_kernel/auth/jwt_utils.py
@dataclass(frozen=True)
class TokenPayload:
    sub: str                              # user email / identifier
    tenant_id: str
    role: str                             # "admin" | "principal" | "teacher" | "parent" | "student"
    exp: datetime
    assigned_sections: tuple[str, ...] = ()   # e.g. ("10-A",) — only meaningful for role == "teacher"
```

`create_access_token` gains an `assigned_sections: list[str] | None = None` parameter and embeds it in the JWT claims (`"assigned_sections": assigned_sections or []`). `decode_access_token` reads it back with `tuple(payload.get("assigned_sections", []))`.

`backend/modules/auth/api/views.py` — extend `_DEMO_USERS` with the new field so teacher tokens actually carry a scope:

```python
_DEMO_USERS: dict[str, dict] = {
    # ... existing admin/principal entries unchanged ...
    "teacher01@demo.school": {
        "password": "Demo@1234!",
        "role": "teacher",
        "full_name": "Mr. Rajesh Kumar",
        "tenant_id": "greenwood-high-001",
        "assigned_sections": ["10-A"],
    },
    "teacher02@demo.school": {
        "password": "Demo@1234!",
        "role": "teacher",
        "full_name": "Ms. Priya Singh",
        "tenant_id": "greenwood-high-001",
        "assigned_sections": ["10-B"],
    },
    # parent/student entries unchanged — they resolve scope via guardian_user_id / email, not sections
}
```

Pass `assigned_sections=user.get("assigned_sections", [])` into `create_access_token(...)` inside `login()`.

> **Data-model note (required, not optional):** the current schema has no teacher→section assignment table. The `assigned_sections` list embedded in the demo credential dict above is a stopgap sufficient for Phase 1. Before Phase 2 (real DB-backed users), add a `teacher_section_assignments(teacher_user_id, tenant_id, class_section_id)` table and populate `assigned_sections` from a real query at login time instead of a hardcoded list.

### 1.2 Role-scoped data access — close the four open list/read endpoints

These endpoints currently scope by `tenant_id` only and must be scoped by **role** as well. Apply this at the facade layer so the API layer stays thin.

**`backend/modules/students/application/facades.py` — `StudentsFacade`**
Add a `role` and `requesting_user_id`/`assigned_sections` parameter to the facade constructor, and apply before pagination:

```python
class StudentsFacade:
    def __init__(
        self,
        tenant_id: str,
        role: str = "admin",
        requesting_user_id: str = "",
        assigned_sections: tuple[str, ...] = (),
    ) -> None:
        self.tenant_id = tenant_id
        self.role = role.lower()
        self.requesting_user_id = requesting_user_id
        self.assigned_sections = set(assigned_sections)

    def _scope_query(self, query):
        """Apply role-based row scoping. Called before any pagination/filtering."""
        if self.role in ("admin", "principal"):
            return query
        if self.role == "teacher":
            if not self.assigned_sections:
                return query.filter(False)  # teacher with no assigned section sees nothing
            return query.join(ClassSection, Student.class_section_id == ClassSection.id).filter(
                ClassSection.display_name.in_(self.assigned_sections)
            )
        if self.role == "student":
            return query.filter(Student.email == self.requesting_user_id)
        if self.role == "parent":
            return query.filter(Student.guardian_user_id == self.requesting_user_id)
        return query.filter(False)  # unknown role — deny by default
```

Apply `_scope_query` inside `list_students()` and `get_student()` before any other filter. `get_student(student_id)` must additionally re-check that the resolved row's `id` is actually inside the scoped set — do not scope only the *list* query and then fetch-by-id unscoped, or a teacher/student/parent can bypass scoping by guessing/enumerating IDs.

**`backend/modules/students/api/views.py`** — update all three endpoints to construct the facade with role context:

```python
facade = StudentsFacade(
    tenant_id=token.tenant_id,
    role=token.role,
    requesting_user_id=token.sub,
    assigned_sections=token.assigned_sections,
)
```

**`backend/modules/attendance/application/facades.py` — `AttendanceFacade`**
Same pattern: `get_summary()` must reject/scope by `assigned_sections` for `teacher` (ignore the client-supplied `section` param if it's outside the teacher's assigned set — do not trust client input to *narrow* scope only; validate it), and must raise `EntityNotFoundError`/return an empty summary for `student`/`parent` roles calling the tenant-wide `/attendance/summary` endpoint. Student/parent access personal attendance exclusively through `/attendance/student/{id}` (already tenant + now identity scoped, see 1.3) or the new personal endpoints in Section 2.

```python
def get_summary(self, section, from_date, to_date, role="admin", assigned_sections=()):
    if role == "teacher":
        allowed = set(assigned_sections)
        if section and section not in allowed:
            raise SecurityViolationError(f"Teacher not assigned to section '{section}'.")
        if not section:
            section = next(iter(allowed), None)  # default to first assigned section
        if not allowed:
            return self._empty_summary()
    if role in ("student", "parent"):
        raise SecurityViolationError("Use /attendance/student/{id} or the personal summary endpoint for this role.")
    # ... existing tenant-scoped query, now additionally filtered by `section` ...
```

**`backend/modules/fees/application/facades.py` — `FeesFacade`**
`list_invoices()` and `get_collection_summary()` follow the identical rule: `admin`/`principal` unrestricted; `teacher` may view invoices only for students in `assigned_sections` (read-only, no `pay_invoice` access — reject `POST /fees/pay-invoice` for `teacher` role at the API layer with `403`); `student`/`parent` must be redirected to `get_student_ledger(student_id)` resolved via their own identity (Section 1.3), never the tenant-wide list.

### 1.3 Fix `.first()` identity resolution — `/parent/child-summary` and `/student/academic-summary`

**`backend/modules/parent/api/views.py`** — replace the tenant-only `.first()` query:

```python
# BEFORE (bug): resolves the first student in the tenant, ignoring the caller
student_row = (
    session.query(Student, ClassSection.display_name)
    .join(ClassSection, Student.class_section_id == ClassSection.id)
    .filter(Student.tenant_id == token.tenant_id)
    .first()
)

# AFTER (fix): resolves the caller's own child via JWT identity
student_row = (
    session.query(Student, ClassSection.display_name)
    .join(ClassSection, Student.class_section_id == ClassSection.id)
    .filter(
        Student.tenant_id == token.tenant_id,
        Student.guardian_user_id == token.sub,
    )
    .first()
)
if not student_row:
    raise HTTPException(status_code=404, detail="No student record linked to this parent account.")
```

> **Multi-child parents:** the current response model (`ChildSummaryResponse`) assumes one child per parent. If a parent has multiple children, `.first()` after the `guardian_user_id` filter will silently pick one. Add a `GET /parent/children` endpoint returning `list[{child_id, child_name, section}]` filtered by `guardian_user_id == token.sub`, and change `child-summary` to accept an optional `?child_id=` query param (still validated against `guardian_user_id == token.sub` before use — never trust a client-supplied `child_id` without that ownership check).

**`backend/modules/student/api/views.py`** — identical fix, using `Student.email == token.sub`:

```python
student_row = (
    session.query(Student, ClassSection.display_name)
    .join(ClassSection, Student.class_section_id == ClassSection.id)
    .filter(
        Student.tenant_id == token.tenant_id,
        Student.email == token.sub,
    )
    .first()
)
if not student_row:
    raise HTTPException(status_code=404, detail="No student record linked to this account.")
```

### 1.4 Lock `tenant_id` on the AI analytics endpoint to the JWT — remove client override

**`backend/modules/ai_analytics/api/views.py`** — `AskQueryRequest.tenant_id` must stop being honored. Remove the field's influence entirely (keep it in the schema only for backward-compatible request bodies, but never read it):

```python
@router.post("/ask", response_model=AskQueryResponse, ...)
async def ask_analytics(
    body: AskQueryRequest,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> AskQueryResponse:
    # SECURITY: tenant_id is NEVER taken from the request body.
    # It is derived exclusively from the verified JWT claim.
    tenant_id = token.tenant_id
    ...
```

If a legitimate need exists for a cross-tenant admin view later, implement it as a **separate, explicitly role-gated** endpoint (`role == "super_admin"` only) rather than an optional override on the tenant-scoped endpoint.

### 1.5 Hardened Python-level RBAC in `GuardedQueryExecutor` — enforce predicates via AST, not string search

This is the core fix. Today, `GuardedQueryExecutor.validate_sql()` receives only `(sql_query, tenant_id)` and checks that the literal substring `"tenant_id"` exists anywhere in the query. It cannot enforce the parent/student guardian predicate because it never receives `role_key` or `user_id`, and it never inspects the AST for the predicate's actual presence.

**`backend/modules/ai_analytics/application/services/guarded_executor.py`** — full replacement logic:

```python
"""
Sub-Module 8.3: GuardedQueryExecutor — hardened.
AST-level enforcement of:
 1. SELECT-only.
 2. Table whitelist.
 3. Row cap.
 4. Tenant isolation (tenant_id predicate on primary table).
 5. Row-level RBAC: for non-admin roles, the AST MUST contain a verifiable
    ownership predicate. This is enforced structurally — never by trusting
    the LLM's compliance with prompt instructions.
"""
from __future__ import annotations
import logging
import time
from typing import Optional
import sqlglot
from sqlglot import exp
from sqlalchemy import text

from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.ai_analytics.domain.dtos import QueryExecutionResultDTO

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    """Raised when generated SQL violates safety or RBAC constraints."""
    pass


# Columns considered valid identity predicates per role. The RBAC check
# passes if ANY of these columns appears in an equality/IN comparison
# against a literal that matches the caller's own identity, anywhere in
# the AST (including subqueries — this is why we walk exp.EQ / exp.In
# globally rather than only inspecting the top-level WHERE).
ROLE_IDENTITY_COLUMNS: dict[str, tuple[str, ...]] = {
    "PARENT": ("guardian_user_id",),
    "STUDENT": ("email", "user_id"),
}


class GuardedQueryExecutor:

    ALLOWED_TABLES = {
        "students",
        "attendance_records",
        "fee_invoices",
        "class_sections",
        "fee_structures",
    }

    def __init__(self, max_limit: int = 500) -> None:
        self.max_limit = max_limit

    # ------------------------------------------------------------------
    # Public entry point — role_key and user_id are now REQUIRED, not optional.
    # ------------------------------------------------------------------
    def execute(
        self,
        sql_query: str,
        tenant_id: str,
        role_key: str,
        user_id: str,
    ) -> QueryExecutionResultDTO:
        start_time = time.monotonic()
        try:
            validated_sql = self.validate_sql(sql_query, tenant_id, role_key, user_id)
        except SecurityViolationError as err:
            logger.error("SQL Validation/RBAC Error: %s", err)
            return QueryExecutionResultDTO(
                executed_sql=sql_query, columns=(), rows=(), row_count=0,
                execution_time_ms=0.0, error=str(err),
            )

        try:
            with SessionLocal() as session:
                res = session.execute(text(validated_sql))
                columns = tuple(res.keys()) if res.returns_rows else ()
                rows = tuple(tuple(r) for r in (res.fetchall() if res.returns_rows else []))
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                logger.info("Query executed in %sms, %d rows", duration_ms, len(rows))
                return QueryExecutionResultDTO(
                    executed_sql=validated_sql, columns=columns, rows=rows,
                    row_count=len(rows), execution_time_ms=duration_ms, error=None,
                )
        except Exception as ex:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            logger.exception("Database query execution error")
            return QueryExecutionResultDTO(
                executed_sql=validated_sql, columns=(), rows=(), row_count=0,
                execution_time_ms=duration_ms, error=f"Execution Error: {ex}",
            )

    # ------------------------------------------------------------------
    def validate_sql(self, sql_query: str, tenant_id: str, role_key: str, user_id: str) -> str:
        parsed = sqlglot.parse_one(sql_query, read="sqlite")

        if not isinstance(parsed, exp.Select):
            raise SecurityViolationError(
                f"Security Policy Violation: Only SELECT queries are permitted. Got: {type(parsed).__name__}"
            )

        for node in parsed.walk():
            if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command)):
                raise SecurityViolationError(f"Forbidden SQL operation detected: {type(node).__name__}")

        tables_in_query = {t.name.lower() for t in parsed.find_all(exp.Table) if t.name}
        invalid_tables = tables_in_query - self.ALLOWED_TABLES
        if invalid_tables:
            raise SecurityViolationError(f"Access Denied: unapproved table(s): {invalid_tables}")

        # Row cap
        limit_node = parsed.args.get("limit")
        if limit_node:
            try:
                if int(limit_node.expression.this) > self.max_limit:
                    parsed = parsed.limit(self.max_limit)
            except Exception:
                parsed = parsed.limit(self.max_limit)
        else:
            parsed = parsed.limit(self.max_limit)

        validated_sql = parsed.sql(dialect="sqlite")

        # Tenant isolation
        if "tenant_id" not in validated_sql.lower():
            raise SecurityViolationError("Multi-tenancy Policy Failure: tenant_id filter is missing.")

        # ── Row-level RBAC — structural enforcement, not string search ──
        role_upper = role_key.upper()
        if role_upper not in ("ADMIN", "PRINCIPAL"):
            self._enforce_identity_predicate(parsed, role_upper, user_id)

        return validated_sql

    def _enforce_identity_predicate(self, parsed: exp.Select, role_upper: str, user_id: str) -> None:
        """
        Walks the FULL AST (including nested subqueries) for an equality or
        IN-subquery comparison that pins one of ROLE_IDENTITY_COLUMNS[role]
        to the caller's own user_id. Raises SecurityViolationError if no
        such predicate is found anywhere in the query.
        """
        identity_columns = ROLE_IDENTITY_COLUMNS.get(role_upper)
        if identity_columns is None:
            raise SecurityViolationError(f"No RBAC identity policy defined for role '{role_upper}'.")

        found = False
        for node in parsed.walk():
            # Direct equality: column = 'literal'
            if isinstance(node, exp.EQ):
                left, right = node.left, node.right
                col = left if isinstance(left, exp.Column) else (right if isinstance(right, exp.Column) else None)
                lit = right if isinstance(right, exp.Literal) else (left if isinstance(left, exp.Literal) else None)
                if col is not None and lit is not None:
                    col_name = col.name.lower()
                    lit_val = lit.this
                    if col_name in identity_columns and str(lit_val) == str(user_id):
                        found = True
                        break
            # IN-subquery: students.id IN (SELECT id FROM students WHERE guardian_user_id = '...')
            if isinstance(node, exp.In) and node.args.get("query"):
                subquery = node.args["query"]
                for sub_node in subquery.walk():
                    if isinstance(sub_node, exp.EQ):
                        left, right = sub_node.left, sub_node.right
                        col = left if isinstance(left, exp.Column) else (right if isinstance(right, exp.Column) else None)
                        lit = right if isinstance(right, exp.Literal) else (left if isinstance(left, exp.Literal) else None)
                        if col is not None and lit is not None and col.name.lower() in identity_columns and str(lit.this) == str(user_id):
                            found = True
                            break
            if found:
                break

        if not found:
            raise SecurityViolationError(
                f"RBAC Policy Failure: query does not contain a verifiable "
                f"{'/'.join(identity_columns)} predicate scoped to the requesting user. "
                f"Cross-user data access is denied by default."
            )
```

Remove `_basic_safety_check` as a silent fallback path for RBAC-relevant roles — a parser failure must **fail closed** (raise `SecurityViolationError`), not fall back to a weaker text-based check, when `role_upper not in ("ADMIN", "PRINCIPAL")`. Admin queries may still use the fallback path for resilience against sqlglot dialect edge cases.

**`backend/modules/ai_analytics/application/services/analytics_facade.py`** — thread the new required arguments through:

```python
exec_result = self._executor.execute(
    gen_sql_dto.sql,
    request.tenant_id,
    role_key=request.current_role_key or "ADMIN",
    user_id=request.current_user_id or "",
)
```

This single change closes the gap: even if the LLM omits the guardian/student predicate, produces a subtly wrong one, or is manipulated via prompt injection in the natural-language question, the executor now rejects the query outright rather than running it.

---

## Section 2: Multi-Role Web Dashboard UI/UX Specification

### 2.1 Role → navigation configuration

Create `web-dashboard/src/config/roleNavigation.ts` as the single source of truth for what each role can see. Every routing decision in `App.tsx` and `Sidebar.tsx` reads from this file — no inline `role === '...'` checks scattered across components.

```typescript
// web-dashboard/src/config/roleNavigation.ts
import { LayoutDashboard, Users, CalendarCheck, CreditCard, Sparkles, ClipboardCheck, CalendarDays, GraduationCap } from 'lucide-react';

export type AppRole = 'admin' | 'principal' | 'teacher' | 'student' | 'parent';

export interface NavItemConfig {
  id: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: string;
}

export const ROLE_NAV_CONFIG: Record<AppRole, NavItemConfig[]> = {
  admin: [
    { id: 'dashboard', label: 'Dashboard Overview', icon: LayoutDashboard },
    { id: 'students', label: 'Students & Roster', icon: Users },
    { id: 'attendance', label: 'Attendance Insights', icon: CalendarCheck },
    { id: 'fees', label: 'Fee Management', icon: CreditCard },
    { id: 'ai-analytics', label: 'AI Chat Query Engine', icon: Sparkles, badge: 'PRO' },
  ],
  principal: [
    { id: 'dashboard', label: 'Dashboard Overview', icon: LayoutDashboard },
    { id: 'students', label: 'Students & Roster', icon: Users },
    { id: 'attendance', label: 'Attendance Insights', icon: CalendarCheck },
    { id: 'fees', label: 'Fee Management', icon: CreditCard },
    { id: 'ai-analytics', label: 'AI Chat Query Engine', icon: Sparkles, badge: 'PRO' },
  ],
  teacher: [
    { id: 'teacher-schedule', label: 'My Schedule', icon: CalendarDays },
    { id: 'teacher-attendance', label: 'Mark Attendance', icon: ClipboardCheck },
    { id: 'ai-analytics', label: 'AI Chat Query Engine', icon: Sparkles, badge: 'PRO' },
  ],
  student: [
    { id: 'student-academics', label: 'Academic & Grades', icon: GraduationCap },
    { id: 'student-attendance', label: 'Attendance Insights', icon: CalendarCheck },
    { id: 'student-fees', label: 'Fee Management', icon: CreditCard },
    { id: 'ai-analytics', label: 'Ask About My Records', icon: Sparkles },
  ],
  parent: [
    { id: 'parent-academics', label: 'Academic & Grades', icon: GraduationCap },
    { id: 'parent-attendance', label: 'Attendance Insights', icon: CalendarCheck },
    { id: 'parent-fees', label: 'Fee Management', icon: CreditCard },
    { id: 'ai-analytics', label: 'Ask About My Child', icon: Sparkles },
  ],
};

export const DEFAULT_TAB_BY_ROLE: Record<AppRole, string> = {
  admin: 'dashboard',
  principal: 'dashboard',
  teacher: 'teacher-schedule',
  student: 'student-academics',
  parent: 'parent-academics',
};

export function normalizeRole(rawRole: string | undefined): AppRole {
  const r = (rawRole || '').toLowerCase();
  if (r === 'admin' || r === 'principal' || r === 'teacher' || r === 'student' || r === 'parent') return r;
  return 'student'; // fail closed to the most restrictive known role, never to admin
}
```

### 2.2 Route protection in `App.tsx`

Replace the flat `switch` with a role-aware router that only ever mounts components the role config allows. This is a **defense-in-depth** measure — the backend scoping in Section 1 is the real security boundary, but the frontend must not even attempt to render an admin-only component for a restricted role, both for UX correctness and to avoid wasted/failing API calls.

```tsx
// web-dashboard/src/App.tsx
import { ROLE_NAV_CONFIG, DEFAULT_TAB_BY_ROLE, normalizeRole } from './config/roleNavigation';
// ... existing imports ...
import { TeacherScheduleScreen } from './features/teacher/TeacherScheduleScreen';
import { TeacherAttendanceScreen } from './features/teacher/TeacherAttendanceScreen';
import { AcademicGradesScreen } from './features/academic/AcademicGradesScreen';
import { PersonalAttendanceScreen } from './features/attendance/PersonalAttendanceScreen';
import { PersonalFeeScreen } from './features/fee-management/PersonalFeeScreen';

const MainContent: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) return <LoginPage />;

  const role = normalizeRole(user?.role);
  const allowedTabIds = new Set(ROLE_NAV_CONFIG[role].map((i) => i.id));

  return (
    <Layout defaultTab={DEFAULT_TAB_BY_ROLE[role]}>
      {(activeTab, setActiveTab) => {
        // Hard guard: never render a tab this role isn't entitled to.
        const tab = allowedTabIds.has(activeTab) ? activeTab : DEFAULT_TAB_BY_ROLE[role];

        switch (tab) {
          case 'dashboard': return <OverviewDashboard setActiveTab={setActiveTab} />;
          case 'students': return <StudentRoster />;
          case 'attendance': return <AttendanceAnalytics />;
          case 'fees': return <FeeDashboard />;
          case 'ai-analytics': return <ChatQueryBox />;

          case 'teacher-schedule': return <TeacherScheduleScreen />;
          case 'teacher-attendance': return <TeacherAttendanceScreen />;

          case 'student-academics':
          case 'parent-academics': return <AcademicGradesScreen viewerRole={role} />;

          case 'student-attendance':
          case 'parent-attendance': return <PersonalAttendanceScreen viewerRole={role} />;

          case 'student-fees':
          case 'parent-fees': return <PersonalFeeScreen viewerRole={role} />;

          default: return <AcademicGradesScreen viewerRole={role} />;
        }
      }}
    </Layout>
  );
};
```

### 2.3 Dynamic `Sidebar.tsx`

```tsx
// web-dashboard/src/components/layout/Sidebar.tsx
import { ROLE_NAV_CONFIG, normalizeRole } from '../../config/roleNavigation';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const { config } = useTenant();
  const { user } = useAuth();
  const role = normalizeRole(user?.role);
  const navItems = ROLE_NAV_CONFIG[role];
  // ... render navItems exactly as before, but sourced from role config ...
  // ... also replace the hardcoded "Tenant: greenwood-high-001" badge with config.tenant_id ...
};
```

### 2.4 New screen: Teacher — Mark Attendance (`web-dashboard/src/features/teacher/TeacherAttendanceScreen.tsx`)

Requirements:
- Section selector restricted to `user.assigned_sections` (from the JWT-derived `User` object — see Section 4.2) — do not render a free-text or full-section dropdown; render only the teacher's own sections, defaulting to the first.
- Student roster for the selected section, fetched from `GET /students?section={section}` — this call is now safely role-scoped server-side per Section 1.2, so it naturally returns only that teacher's students even if the section param were tampered with.
- Per-student tri-state toggle (Present / Absent / Late), matching the mobile app's `MarkAttendanceScreen.tsx` interaction pattern for consistency.
- "Manual Override" modal, reusing the interaction shape of `mobile-app/src/features/attendance/ManualOverrideDialog.tsx`: requires a free-text justification before an override is submitted.
- Submit via `POST /api/v1/attendance/submit` with the existing `AttendanceSubmitRequest` shape (`signals: list[dict]`).

### 2.5 New screen: Teacher — Schedule (`web-dashboard/src/features/teacher/TeacherScheduleScreen.tsx`)

- Daily timetable grid, current period visually highlighted (compare `TimetableEntry.start_time`/`end_time` against client local time).
- Data source: reuse `GET /students/{student_id}/timetable`'s underlying `class_sections` join logic — expose a new lightweight endpoint `GET /timetable/teacher` scoped by `assigned_sections`, or, if timetable data is section-level rather than teacher-level in the current schema, filter the existing timetable generator by `assigned_sections` client-side. Displays: period number, subject, room, section.

### 2.6 New screen: Academic & Grades (shared by student/parent) (`web-dashboard/src/features/academic/AcademicGradesScreen.tsx`)

- Props: `viewerRole: 'student' | 'parent'`.
- Data source: `GET /student/academic-summary` (student) — already identity-fixed in Section 1.3. For `parent`, add an equivalent `GET /parent/academic-summary` following the exact same guardian-resolution pattern as `/parent/child-summary`.
- Renders: term report card table (`SubjectGradeItem[]`), overall percentage/GPA rollup, subject-by-subject breakdown.

### 2.7 New screen: Attendance Insights — personal (`web-dashboard/src/features/attendance/PersonalAttendanceScreen.tsx`)

- Props: `viewerRole`.
- Data source: `GET /attendance/student/{id}` where `{id}` is resolved server-side from JWT identity, **never** passed from the client as an arbitrary path param for this screen — add a companion endpoint `GET /attendance/me` (student) and `GET /attendance/my-child` (parent) that internally resolve identity exactly as Section 1.3 does, then delegate to the existing `AttendanceFacade.get_student_history`.
- Renders: attendance rate gauge, chronic-absentee warning banner (`>= 5 absences`, matching the existing "Chronic Absentees Alert" threshold used in `OverviewDashboard.tsx`), and a scrollable daily log (`StudentAttendanceDay[]`).

### 2.8 New screen: Fee Management — personal (`web-dashboard/src/features/fee-management/PersonalFeeScreen.tsx`)

- Props: `viewerRole`.
- Data source: `GET /fees/me` (student) / `GET /fees/my-child` (parent) — same identity-resolution pattern, wrapping `FeesFacade.get_student_ledger`.
- Renders: invoice ledger table (`FeeInvoiceResponse[]`), overdue-invoice alert banner, and a "Pay Now" button that opens the existing Razorpay sandbox flow (`POST /fees/pay-invoice`) in a modal — reuse `PayInvoiceRequest`/`PayInvoiceResponse` unchanged.

### 2.9 Admin/Principal

No functional change — `ROLE_NAV_CONFIG.admin` and `.principal` are copies of the current full nav. Principal is treated as a full administrative role per the requirement; if a future requirement needs Principal restricted below Admin, only `roleNavigation.ts` needs to change.

---

## Section 3: AI Engine Prompt Contracts & Local Template Interpolation

### 3.1 Design goal

Replace the current post-hoc, question-text-pattern-matching `_compose_summary()` with a contract where the **LLM proposes the phrasing template at generation time** (when it already has full context: the question, the schema, the intended query shape), but **all interpolation of actual data into that template happens locally in Python, after the guarded executor runs** — the LLM never sees a single result row.

### 3.2 Updated system prompt — JSON output contract

Modify `MASTER_SYSTEM_PROMPT_TEMPLATE` in `backend/modules/ai_analytics/application/services/text_to_sql.py`. The LLM must now return a single JSON object, not raw SQL text:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT CONTRACT — JSON ONLY, NO MARKDOWN FENCES, NO PROSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return exactly one JSON object with this shape:

{
  "sql": "<the SQLite SELECT statement>",
  "single_result_template": "<phrasing used when the query returns exactly 1 row>",
  "multi_result_template": "<phrasing used when the query returns >1 rows>",
  "zero_result_template": "<phrasing used when the query returns 0 rows>"
}

TEMPLATE RULES (violating any of these makes the output invalid):
1. Every placeholder in single_result_template/multi_result_template MUST be
   wrapped in curly braces and MUST exactly match a column alias present in
   your own "sql" SELECT list. Example: if your SELECT is
   "SELECT COUNT(*) AS overdue_count FROM fee_invoices ...", the only valid
   placeholder is {overdue_count}.
2. ALWAYS alias every selected column with a short, descriptive snake_case
   name using `AS <alias>` — never leave a column unaliased if it appears
   in a template.
3. multi_result_template MUST include the literal placeholder {row_count}
   (automatically available, do not alias it yourself) and may reference
   any aggregate column alias from the SELECT list. It must NOT assume
   access to individual row values beyond the first row's aliases — for
   per-row detail, phrase it as a summary ("Found {row_count} students with
   overdue fees, totaling ₹{total_outstanding}."), not a per-row narrative.
4. zero_result_template should be genuinely informative, not just "no
   results" — if the question implies a scope your schema cannot satisfy
   (e.g. a grade/class with no enrolled students), say so plainly.
5. Do not include explanations, markdown fences, or any text outside the
   JSON object.
```

### 3.3 Backend: parse, validate, and locally interpolate — never re-send results

**`backend/modules/ai_analytics/domain/dtos.py`** — extend `GeneratedSQLDTO`:

```python
@dataclass(frozen=True)
class GeneratedSQLDTO:
    raw_query: str
    sql: str
    explanation: str
    confidence_score: float
    single_result_template: str = ""
    multi_result_template: str = ""
    zero_result_template: str = ""
```

**`text_to_sql.py`** — `generate_sql()` parses the LLM's JSON response defensively:

```python
import json

def _parse_llm_json(self, raw_response: str) -> dict:
    cleaned = raw_response.strip()
    if "```" in cleaned:
        cleaned = re.sub(r"```[a-zA-Z]*\n?", "", cleaned).replace("```", "").strip()
    try:
        payload = json.loads(cleaned)
        required = {"sql", "single_result_template", "multi_result_template", "zero_result_template"}
        if not required.issubset(payload.keys()):
            raise ValueError("Missing required keys in LLM JSON output.")
        return payload
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM JSON contract violation: %s. Falling back to legacy SQL-only parse.", e)
        # Fallback: treat the whole raw_response as a bare SQL string (legacy path),
        # and synthesize deterministic templates locally — see 3.4.
        return {
            "sql": cleaned,
            "single_result_template": "",
            "multi_result_template": "",
            "zero_result_template": "",
        }
```

**`analytics_facade.py`** — the interpolation step happens strictly after `GuardedQueryExecutor.execute()` returns, using only the locally-fetched `columns`/`rows` — this data never leaves the process boundary again:

```python
def _interpolate_summary(self, gen_sql_dto: GeneratedSQLDTO, exec_result: QueryExecutionResultDTO) -> str:
    row_count = exec_result.row_count

    if row_count == 0:
        return self._resolve_zero_result(gen_sql_dto, exec_result)

    bindings = dict(zip(exec_result.columns, exec_result.rows[0])) if exec_result.rows else {}
    bindings["row_count"] = row_count

    template = gen_sql_dto.single_result_template if row_count == 1 else gen_sql_dto.multi_result_template
    if not template:
        return self._local_fallback_summary(exec_result)  # legacy deterministic path, 3.4

    try:
        return template.format(**bindings)
    except (KeyError, IndexError) as e:
        logger.warning("Template placeholder mismatch (%s) — using local fallback.", e)
        return self._local_fallback_summary(exec_result)
```

**This is the answer to "how do we format without sending the raw result to the LLM":** `template.format(**bindings)` is pure Python string interpolation running inside the backend process. The LLM produced the *shape* of the sentence at generation time — before any query ran — and never sees `bindings` at all.

### 3.4 Smart fallback templates — 0 rows / NULL / execution error / contract violation

Keep and formalize the existing deterministic logic from `_compose_summary` as the **guaranteed-safe fallback path**, used whenever the LLM's JSON contract is violated, a placeholder doesn't match, or `zero_result_template` is empty:

```python
OUT_OF_SCOPE_GRADE_HINTS = ("class 7", "class 8", "class 9", "grade 7", "grade 8", "grade 9", "7th", "8th", "9th", "11th", "12th")

def _resolve_zero_result(self, gen_sql_dto: GeneratedSQLDTO, exec_result: QueryExecutionResultDTO) -> str:
    if gen_sql_dto.zero_result_template:
        try:
            return gen_sql_dto.zero_result_template.format(row_count=0)
        except (KeyError, IndexError):
            pass  # fall through to deterministic fallback
    question_lower = gen_sql_dto.raw_query.lower()
    if any(h in question_lower for h in OUT_OF_SCOPE_GRADE_HINTS):
        return "No records found. Greenwood High currently only has enrolled data for Grade 10 (Class 10-A and Class 10-B)."
    return "No matching records found for your query."

def _local_fallback_summary(self, exec_result: QueryExecutionResultDTO) -> str:
    columns, rows = exec_result.columns, exec_result.rows
    if len(columns) == 1 and any(k in columns[0].lower() for k in ("count", "total")):
        return f"Found {rows[0][0]} matching records."
    if len(rows) == 1 and len(columns) > 1:
        return "Result: " + ", ".join(f"{c}: {v}" for c, v in zip(columns, rows[0]))
    return f"Retrieved {len(rows)} record(s)."
```

Execution errors (`exec_result.error is not None`, including `SecurityViolationError` messages surfaced from Section 1.5) always short-circuit to a fixed, non-LLM message: `f"Could not compute result: {exec_result.error}"` — this is unchanged from the current facade behavior and remains correct.

---

## Section 4: Data Transfer Objects (DTOs) & Interface Alignments

### 4.1 Python — backend DTOs (complete, post-change)

```python
# backend/shared_kernel/auth/jwt_utils.py
@dataclass(frozen=True)
class TokenPayload:
    sub: str
    tenant_id: str
    role: str
    exp: datetime
    assigned_sections: tuple[str, ...] = ()


# backend/modules/ai_analytics/domain/dtos.py
@dataclass(frozen=True)
class ChatTurnDTO:
    role: str                    # "user" | "assistant"
    content: str
    sql: Optional[str] = None


@dataclass(frozen=True)
class NLQueryRequestDTO:
    query: str
    tenant_id: str
    user_role: str
    current_user_id: str
    current_role_key: str
    chat_history: tuple[ChatTurnDTO, ...] = ()
    debug_mode: bool = True          # see Section 4.3 for the production safeguard


@dataclass(frozen=True)
class GeneratedSQLDTO:
    raw_query: str
    sql: str
    explanation: str
    confidence_score: float
    single_result_template: str = ""
    multi_result_template: str = ""
    zero_result_template: str = ""


@dataclass(frozen=True)
class QueryExecutionResultDTO:
    executed_sql: str
    columns: tuple[str, ...]
    rows: tuple[tuple, ...]
    row_count: int
    execution_time_ms: float
    error: Optional[str]


@dataclass(frozen=True)
class ConversationalAnswerDTO:
    question: str
    generated_sql: str
    explanation: str
    columns: tuple[str, ...]
    rows: tuple[tuple, ...]
    row_count: int
    summary_answer: str
    error: Optional[str]
    execution_time_ms: float = 0.0
```

### 4.2 Python — API layer (Pydantic, `backend/modules/ai_analytics/api/views.py`)

```python
class ChatTurnPayload(BaseModel):
    role: str
    content: str
    sql: Optional[str] = None


class AskQueryRequest(BaseModel):
    query: str
    tenant_id: Optional[str] = None     # accepted for schema compatibility, NEVER read (see 1.4)
    chat_history: list[ChatTurnPayload] = Field(default_factory=list)
    debug_mode: bool = Field(True, description="Include raw SQL/timing in the response (dev only — see production safeguard).")


class AskQueryResponse(BaseModel):
    question: str
    summary_answer: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    error: Optional[str] = None
    # Populated ONLY when debug_mode resolves to True server-side (Section 4.3):
    generated_sql: Optional[str] = None
    explanation: Optional[str] = None
    raw_data_table: Optional[dict] = None      # {"columns": [...], "rows": [[...]]} — explicit duplicate of columns/rows for debug clarity
    execution_time_ms: Optional[float] = None
```

### 4.3 Debug mode resolution — production safeguard (required addition)

`debug_mode: bool = True` is explicitly requested as the development-time default for all users. To prevent this from silently shipping to a non-development environment (where it would let a teacher/student/parent see raw SQL and execution internals for other users' scoped-but-still-sensitive queries), resolve the *effective* debug flag server-side as the AND of the client's request and the deployment environment — never trust the client flag alone in a non-dev environment:

```python
# backend/modules/ai_analytics/api/views.py
from config.settings.base import ENVIRONMENT

async def ask_analytics(body: AskQueryRequest, token: TokenPayload = Depends(get_current_tenant_context)) -> AskQueryResponse:
    tenant_id = token.tenant_id
    effective_debug = body.debug_mode and ENVIRONMENT == "development"
    ...
    return AskQueryResponse(
        ...,
        generated_sql=ans_dto.generated_sql if effective_debug else None,
        explanation=ans_dto.explanation if effective_debug else None,
        raw_data_table={"columns": list(ans_dto.columns), "rows": [list(r) for r in ans_dto.rows]} if effective_debug else None,
        execution_time_ms=ans_dto.execution_time_ms if effective_debug else None,
    )
```

This preserves the literal requirement (`debug_mode: bool = True` for all users during development) while making "during development" an enforced fact rather than an assumption. Before promoting to a staging/production environment, additionally gate `effective_debug` on `token.role.upper() in ("ADMIN", "PRINCIPAL")` if any non-admin access to this endpoint is expected to remain in that environment.

### 4.4 TypeScript — `web-dashboard/src/types/index.ts` additions

```typescript
export type AppRole = 'admin' | 'principal' | 'teacher' | 'student' | 'parent';

export interface User {
  sub: string;
  role: AppRole;
  full_name: string;
  tenant_id: string;
  assigned_sections?: string[];   // present only for role === 'teacher'
}

export interface ChatTurnPayload {
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
}

export interface AskQueryRequest {
  query: string;
  chat_history: ChatTurnPayload[];
  debug_mode: boolean;
}

export interface RawDataTable {
  columns: string[];
  rows: any[][];
}

export interface AIQueryResponse {
  question: string;
  summary_answer: string;
  columns: string[];
  rows: any[][];
  row_count: number;
  error?: string;
  // Present only when debug_mode is active AND resolved true server-side:
  generated_sql?: string;
  explanation?: string;
  raw_data_table?: RawDataTable;
  execution_time_ms?: number;
}

export interface AcademicSubjectGrade {
  subject_name: string;
  teacher_name: string;
  grade: string;
  score_pct: number;
}

export interface PersonalAcademicSummary {
  student_id: string;
  student_name: string;
  section: string;
  roll_number: number;
  attendance_rate_pct: number;
  report_card: AcademicSubjectGrade[];
  timetable_count: number;
}
```

`AttendanceSummary`, `FeeSummary`, `FeeInvoice`, `Student`, `TimetableEntry` are unchanged — the new personal screens (Section 2.7, 2.8) reuse `StudentAttendanceHistory`-equivalent and `StudentFeeLedger`-equivalent shapes already defined; only add the two new interfaces above (`AcademicSubjectGrade`, `PersonalAcademicSummary`) since no TS interface currently models the report card response.

---

## Section 5: Step-by-Step Antigravity Execution Blueprint

Execute strictly in this order. Each step depends on the previous one being merged and passing its own verification before the next begins — do not parallelize steps 1–3.

**Step 1 — Backend security hardening (Section 1).**
Implement JWT `assigned_sections` claim, role-scoped `StudentsFacade`/`AttendanceFacade`/`FeesFacade`, the `.first()` → JWT-identity fix in `/parent/child-summary` and `/student/academic-summary`, the `tenant_id` lock on `/ai-analytics/ask`, and the AST-level RBAC enforcement in `guarded_executor.py` + the new `execute()` signature threaded through `analytics_facade.py`.
*Verify:* write/extend `backend/tests/test_e2e_pipeline.py` with cases asserting (a) a teacher token cannot list students outside `assigned_sections`, (b) a parent token against `/parent/child-summary` returns only their own guardian-linked child, (c) a hand-crafted SQL string missing the guardian predicate is rejected by `GuardedQueryExecutor` for a `PARENT` role token even though it passes the old tenant-only check.

**Step 2 — AI engine prompt contract + local interpolation (Section 3).**
Update `MASTER_SYSTEM_PROMPT_TEMPLATE` to the JSON output contract, implement `_parse_llm_json`, extend `GeneratedSQLDTO`, implement `_interpolate_summary` / `_resolve_zero_result` / `_local_fallback_summary` in `analytics_facade.py`.
*Verify:* run `backend/tests/benchmark_rag_50.py` and `run_user_50_questions.py` / `run_user_questions_51_100.py` against the new contract; confirm zero raw row data appears in any outbound LLM request payload (grep the request-building code path for any reference to `exec_result.rows` before the executor has run — there must be none, by construction, since interpolation only happens after execution).

**Step 3 — DTO / interface alignment (Section 4).**
Apply all Python DTO/Pydantic changes and all TypeScript interface additions. Regenerate/hand-sync the API client types in `web-dashboard/src/api/client.ts` usage sites and `mobile-app/src/types/index.ts` if the mobile app also calls `/ai-analytics/ask` or the personal endpoints.
*Verify:* `tsc --noEmit` clean on `web-dashboard/`; backend Pydantic models importable with no field default/type errors; confirm `AskQueryResponse` debug fields are `Optional` everywhere they're consumed in the frontend (no non-null assertions on `generated_sql` etc.).

**Step 4 — Web dashboard role routing + new screens (Section 2).**
Add `roleNavigation.ts`, update `App.tsx` and `Sidebar.tsx` to consume it, build the five new screen components (`TeacherScheduleScreen`, `TeacherAttendanceScreen`, `AcademicGradesScreen`, `PersonalAttendanceScreen`, `PersonalFeeScreen`) and their four new backend endpoints (`/attendance/me`, `/attendance/my-child`, `/fees/me`, `/fees/my-child`, `/parent/academic-summary`) using the identity-resolution pattern from Section 1.3.
*Verify:* manual smoke test logging in as each of the 5 demo roles (`SEED_CREDENTIALS.md`) — confirm sidebar nav matches `ROLE_NAV_CONFIG` exactly, confirm no admin-only tab is reachable by URL/state manipulation for restricted roles (the `allowedTabIds` guard in `App.tsx` must redirect, not error).

**Step 5 — Debug mode wiring end-to-end (Section 4.2, 4.3).**
Wire `debug_mode` through `NLQueryRequestDTO` → `AskQueryRequest`/`AskQueryResponse`, implement the `ENVIRONMENT == "development"` server-side safeguard, add the frontend toggle + collapsible "View generated SQL / execution details" panel in `ChatQueryBox.tsx` (visible only when `raw_data_table`/`generated_sql` are present in the response, i.e. naturally hidden outside development without any frontend role-check needed).
*Verify:* confirm `AskQueryResponse.generated_sql` is `null` when `ENVIRONMENT=production` is set locally regardless of the request's `debug_mode` value; confirm it is populated in `development`.

**Step 6 — Full regression & sign-off.**
Run the complete backend test suite (`backend/tests/`), the manual 5-role smoke test from Step 4 extended to also cover attendance-marking (teacher), report-card viewing (student/parent), and the Razorpay sandbox pay flow (student/parent). Re-run the two AI-analytics adversarial cases from Step 1's verification against the **fully integrated** system (not the isolated executor) to confirm the fix holds end-to-end through the real LLM call path, not just the guardrail unit. Only after all of the above pass does this correction set merge.
