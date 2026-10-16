# Maintained verification cases: Panel creation menu

All cases use synthetic notes and non-unique GTK test applications or a private
X11/session bus. Preconditions: a fresh in-memory/disposable schema-6 library,
one live profile with Shared, and ordinary groups created only as stated. No
user data or credentials are used. Cleanup destroys test windows and closes
stores; native checks stop/reap their tray helper and remove temporary data.

| ID / title | Traceability | Risk / classification | Objective and Given / When / Then | Automation |
| --- | --- | --- | --- | --- |
| NEW-T01 Choose note destination | NEW-01,02 / AC-01,02 | Medium / GTK integration | Given Shared-only and ordinary contexts, when opening/dismissing New or selecting New Note, then dismissal writes nothing and creation targets Shared or the active ordinary group without a persistent mode. | Automated: test_panel_creation_menu |
| NEW-T02 Group creation and cancellation | NEW-03 / AC-03,04 | Medium / GTK integration | Given an active project, when selecting New Group…, cancelling, retrying a reserved name and then creating Project B, then only successful creation changes context and New still offers both actions. | Automated: test_panel_creation_menu |
| NEW-T03 Keyboard and space | NEW-04,05 / AC-05 | Medium / native UI | Given a normal/narrow dark panel, when using keyboard Enter, Tab and Escape, then the menu exposes both named actions, deliberate selection opens the correct flow, cancellation returns focus, and the body has no separate group button. | Automated native harness; screenshot inspection |

This UI slice needs no new storage-failure, migration, credential or network
cases. Existing organization dialog/controller tests cover validation and save
failures; the full suite protects those paths. Execution history is separate
from this case design in [execution.md](execution.md).
