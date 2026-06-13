# AI Note Creation Ideas

## Purpose

Capture early thinking for AI-assisted note creation without making it part of
the immediate local MVP roadmap.

## Candidate Experience

The user writes or speaks a command such as:

```text
crie uma nota para me lembrar de ir ao médico dia 5 às 9am
```

Pinleaf interprets the request and creates a note with useful text, color and
possibly future reminder metadata.

## Possible Capabilities

- Text command palette for creating notes.
- Voice input through desktop speech-to-text.
- AI-generated note title/body.
- Optional extraction of date/time.
- Later integration with reminders or calendar.

## Integration Options

- User-configured API token.
- Login-based provider integration.
- Local API proxy controlled by the maintainer.
- Future account system shared with sync.

## Open Questions

- Should AI be optional and disabled by default?
- Which provider should be supported first?
- Should Pinleaf send full note content or only the user prompt?
- Should prompts and outputs be logged locally?
- Should date/time extraction create reminders or only note text?

## Risks

- Privacy concerns if note content is sent to an external provider.
- Token storage and revocation.
- Network failures creating unreliable UX.
- Voice input adds OS-level dependency and permission complexity.

## Suggested Timing

Revisit after local note behavior is stronger: position persistence,
always-on-top and per-note appearance.

