# Feature: Pinleaf project page and screenshots

## Intent

Problem:
Pinleaf has a public GitHub repository and an app website URL in the About
dialog, but the project page does not exist yet. The README also lacks visual
context for new visitors.

Users or stakeholders:
Potential users, contributors and maintainers visiting the GitHub repository or
project website.

Desired outcome:
Pinleaf has a small static project page suitable for GitHub Pages and the README
can show or link to screenshots that demonstrate the MVP.

Non-goals:
- Marketing site with analytics.
- Documentation portal.
- Download/release automation.
- Package distribution.
- Dynamic site generation.

## Scope

In scope:
- Static GitHub Pages-ready files under the repository.
- Screenshot asset locations.
- README link to the project page and selected screenshots.
- Basic content: app description, features, run instructions, known limitations
  and repository links.

Out of scope:
- Custom domain.
- GitHub Pages deployment automation beyond repository files.
- Browser-based demo.
- Release downloads.
- Screenshot capture automation.

Assumptions:
- GitHub Pages URL is `https://robmoraes.github.io/pinleaf/`.
- Screenshots will be prepared manually by the maintainer.
- The page can be plain HTML/CSS for now.

Dependencies:
- Existing README, known limitations and app assets.
- Screenshots provided by the maintainer.

## Behavior

1. The repository contains a static project page entrypoint.
2. The project page explains what Pinleaf is in one short paragraph.
3. The project page shows core MVP features.
4. The project page references local development install instructions.
5. The project page includes screenshots when image files are available.
6. The README links to the GitHub Pages URL.
7. Missing screenshots should not block the initial page from rendering.

## Acceptance Examples

Scenario: view project page locally
Given the repository contains the static page
When a contributor opens the page in a browser
Then the page shows Pinleaf's name, description, feature list and run/install
instructions.

Scenario: screenshots are added
Given screenshot files exist under the documented assets path
When the project page is opened
Then screenshots are displayed with descriptive alt text.

Scenario: README directs visitors
Given a user opens the repository README
Then the README includes a link to the project page URL.

## Data and Contracts

Inputs:
- Static screenshots.
- Existing project metadata.

Outputs:
- Static HTML/CSS files.
- README links.

API/schema/event changes:
- None.

Persistence changes:
- None.

## Quality Attributes

Security:
- The static page must not include analytics, remote scripts or tracking.

Privacy:
- No telemetry.

Accessibility:
- Screenshots must have alt text.
- Text contrast must be readable.
- The page should work without JavaScript.

Performance:
- Keep page assets small enough for quick loading.

Reliability:
- Page should render even before screenshots are added.

Observability:
- None.

## Rollout and Operations

Migration:
- None.

Feature flag or configuration:
- GitHub Pages must be enabled in repository settings after files are pushed.

Rollback:
- Revert the static page commit.

Monitoring:
- None.
