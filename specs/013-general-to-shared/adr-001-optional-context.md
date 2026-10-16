# ADR 001: Shared identity and optional ordinary context

Status: accepted under the maintainer's pre-approved plan, 2026-10-11.

## Context

Shared is always available within a profile and cannot be activated. Schema 5
requires an active group and derives the profile from it. Retaining that model
would make Shared look active or force an unwanted ordinary group into existence.

## Decision

Use schema 6 with explicit active profile and nullable ordinary group. Store
nullable per-profile last group. Rename the captive role to is_shared and keep
the existing group's ID and note memberships. Rebuild only the context tables
for schema-5 libraries; note rows do not require rebuilding or retimestamping.
Foreign keys enforce ownership; service guards and context validation reject
Shared as an ordinary context. Metadata recovery clears stale ordinary references.

Use one visibility rule for Shared plus the optional ordinary group. Preserve
editor instances in the intersection across switches. Store migration notices
separately from existing user settings so preservation checks remain exact.

## Alternatives

- Treat Shared as active internally: conflicts with the agreed domain rule and
  obscures creation/search semantics.
- Always create an ordinary General: adds an unwanted group and makes direct
  conversion ambiguous.
- Split one note into multiple memberships: unnecessary duplication of domain
  complexity for notes common to a whole profile.

## Consequences

All context consumers must handle an absent ordinary group. Older binaries must
refuse schema 6. A validated pre-upgrade snapshot remains the rollback boundary.
Local behavior requires no new dependency, network service or credential setup.
