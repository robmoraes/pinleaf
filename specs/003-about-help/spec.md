# Feature: Pinleaf about and help

## Intent

Problem:
Pinleaf is ready enough for public repository use, but the app itself does not
expose basic identity, credits, maintainer or license information.

Users or stakeholders:
Early users, reviewers and maintainers evaluating Pinleaf from the desktop app.

Desired outcome:
Pinleaf provides a native about/help dialog with concise project information,
maintainer credits, license and bundled font credits.

Non-goals:
- Full help system.
- Changelog viewer.
- Dynamic build metadata.
- Auto-update information.
- Embedded web documentation.

## Scope

In scope:
- A native libadwaita about/help dialog.
- An `About Pinleaf` action in the main panel.
- Static metadata constants for version and build date placeholders.
- Maintainer name and website.
- Short app description.
- MIT license reference.
- Bundled font credit.

Out of scope:
- Dynamically reading version from installed package metadata.
- Dynamically generating build date.
- Opening local documentation pages inside the app.
- Per-font detailed license text in the dialog.

Assumptions:
- Version and build date can be placeholders for now.
- Detailed font license files remain in `pinleaf/resources/fonts`.
- The app already uses GTK 4 and libadwaita.

Dependencies:
- libadwaita about dialog/window support available through PyGObject.

## Behavior

1. The main panel exposes an `About Pinleaf` action.
2. Activating `About Pinleaf` opens a native about/help dialog.
3. The dialog shows the app name `Pinleaf`.
4. The dialog shows version placeholder `0.1.0-dev`.
5. The dialog shows build date placeholder `TBD`.
6. The dialog shows maintainer `robmoraes`.
7. The dialog links to `https://about.robmoraes.dev.br`.
8. The dialog includes a short description of the app.
9. The dialog identifies the app license as MIT.
10. The dialog credits bundled Google Fonts under the SIL Open Font License.

## Acceptance Examples

Scenario: view about information
Given the Pinleaf main panel is open
When the user activates `About Pinleaf`
Then a native about/help dialog opens
And it shows the app name, version placeholder, build date placeholder,
maintainer, website, description and license.

Scenario: review credits
Given the about/help dialog is open
Then the user can see that bundled fonts are credited under the SIL Open Font
License.

## Data and Contracts

Inputs:
- User action from the main panel.

Outputs:
- Native about/help dialog.

API/schema/event changes:
- None.

Persistence changes:
- None.

## Quality Attributes

Security:
- External website is shown as a URL; the app does not fetch remote content for
the dialog.

Privacy:
- Opening the dialog does not send telemetry or network requests.

Accessibility:
- The action label and dialog content should be readable by assistive
technology through standard GTK/libadwaita widgets.

Reliability:
- Missing optional about fields must not crash the app.

Observability:
- None required.

## Rollout and Operations

Migration:
- None.

Feature flag or configuration:
- None.

Rollback:
- Remove the about action and dialog helper.

Monitoring:
- None.
