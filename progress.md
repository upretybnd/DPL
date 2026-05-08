# Progress Log

## Completed
- Rebuilt missing Django settings and restored project bootability.
- Fixed startup/runtime blockers (`dpl.settings` missing, lazy `reportlab` import, safer `test.py`).
- Made branch pages database-driven (removed hardcoded branch IDs in listing/detail flow).
- Integrated homepage media from DB with static fallback images.
- Added `HomePageMedia` model and migration.
- Implemented Phase 1 reporting module:
  - New `reports` app with role-based access (`National Admin`, `Branch Admin`, `Reporter`, `Viewer`).
  - Models for project reporting workflow, comments, status history, evidence, beneficiary stats.
  - Branch and national dashboards.
  - Project create/detail/submit/review endpoints.
  - Admin registration for reporting entities.
  - UI enhancement for reporting pages (cards, badges, responsive tables/forms).

## Completed (Phase 2)
- Added monthly reporting period model with lock/unlock support:
  - `ReportingPeriod(year, month, is_locked, locked_at)`
- Added evidence requirement model by project type:
  - `EvidenceRequirement(project_type, evidence_type, is_required)`
- Enforced submission validation:
  - Block submit if reporting period is locked.
  - Block submit when required evidence types are missing.
- Added PDF exports:
  - Project report PDF export endpoint.
  - Branch monthly summary PDF export endpoint.
- Added national dashboard controls:
  - Toggle lock/unlock for reporting periods.
  - Display recent period states.
- Added dashboard/detail UI actions:
  - Export project PDF button.
  - Export monthly branch PDF button.
- Created and applied migrations:
  - `reports/migrations/0002_reportingperiod_evidencerequirement.py`

## Current State
- `python manage.py check` passes.
- `reports` migrations are applied through `0002`.
- Phase 1 + Phase 2 features in `progress.md` are complete.

## Suggested Next (Phase 3)
- Rich analytics (trend charts, branch rankings, SDG distribution).
- Public transparency pages for approved/published projects.
- Better PDF layout templates (branding, sections, totals).
