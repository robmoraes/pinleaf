# Plan: Ubuntu PPA publication

## Spec Link

- Source spec: `docs/.specs/009-ubuntu-ppa/spec.md`
- Tracking issue: `https://github.com/robmoraes/pinleaf/issues/13`

## Approach

Extend the existing Debian packaging work from spec 008 from local binary `.deb`
builds to Launchpad source-package publication.

The first iteration uses the personal PPA `ppa:robmoraes/pinleaf`, not a
Launchpad team. The process should remain manual until the source package,
Launchpad build and install flow are proven end to end.

The implementation should focus on:

- making the existing `debian/` package acceptable for source-package upload;
- defining a version and target Ubuntu series suitable for Launchpad;
- building and signing a source package locally;
- uploading the source package with `dput`;
- validating Launchpad build output and PPA installation;
- documenting the final install flow after validation.

## Implementation Notes

- Use the existing source format unless source-package validation shows it must
  change.
- Review `debian/changelog` for Launchpad-compatible version and distribution.
- Keep package architecture as `all`.
- Keep runtime dependencies aligned with Ubuntu package names already validated
  during local `.deb` testing.
- Avoid adding maintainer scripts unless required.
- Do not automate GPG private key handling in GitHub Actions in this iteration.
- Treat GitHub Release `.deb` artifacts as an alternative distribution channel,
  not as the source for the PPA.

## Files

Expected changed areas:

- `debian/`: package metadata, changelog or source-package fixes if required.
- `README.md`: PPA install documentation after successful validation.
- `docs/site/index.html`: GitHub Pages install section after successful
  validation.
- `CHANGELOG.md`: release-visible PPA distribution support.
- `docs/.specs/009-ubuntu-ppa/`: this spec and validation notes.

Expected temporary or external artifacts:

- source package files generated next to the repo by Debian tooling;
- Launchpad upload/build records;
- manual test notes under `tmp/`.

## Validation

Automated:

- run `/usr/bin/python3 -m unittest discover -s tests`;
- run `/usr/bin/python3 -m compileall pinleaf tests`;
- build a source package with Debian tooling;
- verify the generated source `.changes` is signed.

External:

- upload the signed source package with:

```bash
dput ppa:robmoraes/pinleaf <source.changes>
```

- confirm Launchpad accepts the upload;
- monitor Launchpad build logs;
- confirm the package is published.

Manual:

- add the PPA on a clean Ubuntu system;
- install Pinleaf with `sudo apt install pinleaf`;
- launch Pinleaf from terminal;
- launch Pinleaf from desktop application search;
- remove and reinstall the package;
- confirm existing user note data is preserved.

## Risks

- Launchpad source builds may expose missing build dependencies that local
  binary builds did not catch.
- Ubuntu target-series naming or versioning may need adjustment before upload.
- GPG signing and `dput` configuration are local maintainer concerns and may
  fail independently of repository code.
- PPA publication can take time because Launchpad builds are asynchronous.
- Documentation should not make the PPA the primary install path until a
  published package is validated.
