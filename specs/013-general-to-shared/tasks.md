# Tasks: General to Shared

Status: T01–T08 complete on 2026-10-11. Shared is implemented, verified and
published for review in [draft PR #28](https://github.com/robmoraes/pinleaf/pull/28).
Evidence: [execution record](execution.md).
Sources: [spec](spec.md), [plan](plan.md), [contract](contracts/general-to-shared.json).

- [x] **T01 — Accept decisions and finalize contracts.** Record CR-02 acceptance,
  schema 6, ADR and maintained verification cases. Validate JSON, links and IDs.
- [x] **T02 — Migrate existing libraries safely.** Convert General in place,
  handle reserved-name collisions, preserve tombstones, rebuild nullable context,
  persist the notice and retain snapshot/transaction safeguards. Verify schemas
  1–5, source notes/settings/IDs, General/ordinary active contexts, interruption,
  forced failures, fresh setup and repeat startup. Covers AC-01,02,11,12.
- [x] **T03 — Implement Shared domain/context.** Update models, name rules,
  explicit profile activation and nullable recovery. Reject Shared activation;
  preserve valid absence on restart and profile return. Covers AC-02,04,06,11.
- [x] **T04 — Implement creation, search and disposal.** Add Shared creation,
  current-context union and cross-profile Shared open. Adapt move/delete and
  stale replacement checks. Verify metadata preservation, hidden/deleted notes
  and no implicit context changes. Covers AC-05..10.
- [x] **T05 — Preserve shared editor windows.** Update the controller and app
  wiring to reuse eligible windows, save pending edits, restore both contexts
  and detect profile changes with NULL ordinary groups. Verify window identity,
  failure rollback, restart and movement. Covers AC-03,04,07,13.
- [x] **T06 — Complete GTK UX.** Shared expander/+ and row actions, nullable title,
  search scope/results, deletion summaries and dismissible migration notice.
  Verify controls, focus, keyboard operation and normal/narrow layouts with
  isolated data; capture screenshots. Covers AC-04..11.
- [x] **T07 — Document and qualify.** Update development docs and Unreleased,
  run unittest/compileall/diff checks, schema-5 recovery drill, native lifecycle
  and representative switch benchmark. Record evidence and platform limits.
- [x] **T08 — Publish reviewable work.** Review the complete diff, commit/push
  and create/update the feature PR with spec, behavior, validation and limits.
  Leave package release/tag/merge for the later release decision.

## Scope Control

No New menu or remote integration implementation is included. Qualification
uses disposable libraries, not the installed user's note database. Cleanup of
test windows, tray helpers and sessions is part of each native verification.
