\# AI Analytics Engine \& Chat UI Correction Specification (`update.md`)



\*\*Target File:\*\* `smart-academic-erp/update.md`  

\*\*Components:\*\* Backend (`text\_to\_sql.py`, `guarded\_executor.py`, `analytics\_facade.py`) \& Web Frontend (`ChatQueryBox.tsx`)



\---



\## 1. FIX: SQLite OperationalError \& Enable Teacher Queries



\### Root Cause:

Dangling `WHERE tenant\_id = '...'` in fallback queries without a `FROM` table crashes SQLite with `sqlite3.OperationalError: no such column: tenant\_id`. Furthermore, teacher queries fail because the LLM needs a clear rule mapping teachers to `users WHERE role\_key = 'TEACHER'`.



\### Required Backend Fixes:

1\. \*\*Fix Out-of-Scope Fallback SQL (`guarded\_executor.py` / `text\_to\_sql.py`):\*\*

&#x20;  - Never generate `SELECT ... WHERE tenant\_id = ...` without a valid `FROM` table.

&#x20;  - If a query is determined to be out of scope or invalid, return a safe statement:

&#x20;    `SELECT 'No matching records found' AS message;`

2\. \*\*Add Teacher Schema Mapping \& Few-Shot Exemplar (`text\_to\_sql.py`):\*\*

&#x20;  - Add explicit system prompt instruction:

&#x20;    > \*"To list teachers or staff, query the `users` table filtering by `LOWER(role\_key) = 'teacher'` or `LOWER(role\_key) = 'principal'`."\*

&#x20;  - Add Few-Shot Exemplar:

&#x20;    ```text

&#x20;    Q: "List all teachers in my school"

&#x20;    SQL:

&#x20;    SELECT full\_name, email, phone 

&#x20;    FROM users 

&#x20;    WHERE tenant\_id = '{tenant\_id}' 

&#x20;      AND LOWER(role\_key) = 'teacher' 

&#x20;      AND {rbac\_predicate};

&#x20;    ```



\---



\## 2. REFACTOR: Chat UI Component (`ChatQueryBox.tsx`)



\### UX Requirement:

The Data Table MUST BE ALWAYS VISIBLE to normal users/admins below the answer sentence. The "Developer Mode" toggle controls ONLY the visibility of technical SQL execution logs.



\### Frontend Changes:

1\. \*\*Add `🛠️ Dev Mode` Header Toggle Button:\*\*

&#x20;  - Add a styled button in the Chat Header: `🛠️ Dev Mode (Show SQL)`.

&#x20;  - Store boolean state `showDevDetails` (default: `true` in development, `false` in production).

&#x20;  - Pass `debug\_mode: showDevDetails` in payload to `POST /api/v1/ai-analytics/ask`.



2\. \*\*UI Component Rendering Order:\*\*

&#x20;  - \*\*Always Render (Normal Admin View):\*\*

&#x20;    1. `summary\_answer`: Conversational intro sentence (e.g., \*"Here are the 5 teachers in Greenwood High:"\*).

&#x20;    2. `DataTable Component`: Primary styled table displaying `columns` and `rows` (e.g., Student Name, Phone, Fees, Attendance). \*\*This table must NEVER be hidden behind developer accordions.\*\*

&#x20;  - \*\*Conditionally Render (Developer Debug View — shown ONLY when `showDevDetails === true`):\*\*

&#x20;    \* Collapsible accordion `> View Generated SQL \& Execution Details` showing `generated\_sql`, `execution\_time\_ms`, and `explanation`.



\---



\## 3. ENHANCE: Conversational Summary Sentences (`analytics\_facade.py`)



\### Backend Changes:

1\. \*\*Natural Intro Sentences (`\_interpolate\_summary`):\*\*

&#x20;  - Ensure `summary\_answer` returns an informative, conversational intro sentence above the data table, e.g.:

&#x20;    \* For teacher queries: \*"Here are the registered teachers for Greenwood High:"\*

&#x20;    \* For absenteeism queries: \*"Here are the top 5 students with the highest absenteeism in 2026, along with parent contact details:"\*

&#x20;    \* For fee queries: \*"Here is the fee invoice status breakdown for Greenwood High:"\*

&#x20;  - If 0 rows return, output: \*"No matching records found for your query."\* (or explain grade limits if Grade 8/9 is requested).



\---



\## 4. Verification Checklist



1\. \*\*Test Teacher Query:\*\*

&#x20;  - Ask: `"list name of all teachers in my school"`

&#x20;  - \*\*Verify:\*\* Returns SQL `SELECT full\_name, email, phone FROM users WHERE LOWER(role\_key) = 'teacher'` and displays Mr. Rajesh Kumar and Ms. Priya Singh in the primary Data Table! Zero SQLite errors.

2\. \*\*Test Dev Mode Toggle:\*\*

&#x20;  - Toggle `🛠️ Dev Mode` OFF: Confirm raw SQL accordion disappears, but the \*\*Data Table remains 100% visible\*\* below the intro sentence.

&#x20;  - Toggle `🛠️ Dev Mode` ON: Confirm raw SQL accordion appears above the Data Table.

