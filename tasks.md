# Reporting Module Task Guide

This document explains what is implemented and how each team can use it.

## Implemented Features

1. Branch and national dashboards
- Branch dashboard with project KPIs and monthly PDF export.
- National dashboard with cross-branch summary and reporting period lock/unlock.

2. Project reporting workflow
- Create project report drafts.
- Submit drafts for review (with period-lock and required-evidence validation).
- National review actions: `review`, `approve`, `reject`.
- Approved projects can be published publicly.

3. Evidence management
- Add evidence directly from project detail.
- Evidence validation requires file or external URL.
- Delete evidence (branch managers/reporters only).
- Required evidence enforcement before submit.

4. Analytics and exports
- National analytics page with:
  - Monthly trends
  - Branch rankings
  - SDG distribution
- Analytics CSV export.

5. Public transparency
- Public reports list for approved + published projects only.
- Public project detail pages.
- Filters: search, branch dropdown, year dropdown, month dropdown, SDG.
- Pagination for public list.

6. Governance, audit, and notifications
- Immutable audit log records key actions.
- Audit log page + CSV export.
- In-app notifications page for users.
- Reminder action for missing evidence in selected period.
- Lock/unlock period notifications to branch-level users.

7. Data quality controls
- SDG tag format validation (`SDG 1` to `SDG 17`).
- Budget validation (`budget_actual <= budget_planned` when planned > 0).

8. PDF templates
- Project PDF export with branded header and structured sections.
- Branch monthly PDF export with totals and structured project listing.

## Team Usage by Role

## National Team (National Admin)

Primary URLs:
- `/reports/dashboard/national/`
- `/reports/dashboard/national/analytics/`
- `/reports/dashboard/national/audit-logs/`

Main tasks:
1. Lock or unlock reporting periods (`YYYY-MM`).
2. Review submitted projects:
   - Mark as reviewed
   - Approve or reject (with notes)
3. Send evidence reminders for a period.
4. Monitor branch performance in analytics.
5. Export analytics and audit logs to CSV.
6. Monitor public transparency page content.

## Branch Team (Branch Admin / Reporter)

Primary URLs:
- `/reports/dashboard/branch/`
- `/reports/projects/new/`
- `/reports/projects/<project_id>/`

Main tasks:
1. Create project report draft.
2. Add report details and evidence.
3. Ensure required evidence is complete.
4. Submit for national review.
5. Track status timeline and comments.
6. Export monthly branch PDF.
7. Check notifications for review outcomes/reminders.

## Viewer Role

Primary URLs:
- `/reports/dashboard/branch/`
- `/reports/projects/<project_id>/` (view access only for permitted branches)

Main tasks:
1. View branch reports and status.
2. View project details and exports where permitted.

## Public Users

Primary URLs:
- `/reports/public/projects/`
- `/reports/public/projects/<project_id>/`

Main tasks:
1. Browse approved/published project reports.
2. Filter by branch, year, month, SDG, and keyword.

## Suggested Operations Checklist

Daily:
1. Branch teams review notifications and pending drafts.
2. National team checks newly submitted projects.

Weekly:
1. National team reviews analytics trends and rankings.
2. Branch teams export monthly/period progress PDFs as needed.

Monthly:
1. National team locks completed period.
2. National team exports audit and analytics CSV for governance review.
3. National team verifies public transparency pages for approved projects.

## Validation Status

Latest local verification:
1. `python manage.py check` passed.
2. `python manage.py test reports` passed.
