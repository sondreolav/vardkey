# Updating VardKey

VardKey is our own application, and the package builds it from the source in this repository rather
than from a published upstream image or a git submodule. There is therefore no external upstream
version to track, and no upstream artifact to verify before a bump.

## Determining the upstream version

There is no upstream. The application source (`app.py`, `database.py`, `alerts.py`, `export.py`,
`validation.py`, `auth.py`, `maintenance.py`, `secret_guard.py`, and `static/`) lives at the
repository root, and that is what the `Dockerfile` copies into the image. The application carries no
version number of its own, so nothing outside this repository has to be checked before a release.

The application's database schema has its own version (currently **13**), which is handled inside
`database.py` and has nothing to do with the package version. The package needs no data migration of
its own: the application migrates its schema itself on startup, so `startos/versions/` stays empty.
A package change that did need one would put its `up`/`down` there, not in the application.

## The version scheme

The package version is **date based**: `YYYY.MM.DD:revision`, where the date is the day the package
is released — not the day of the application change it carries — and the revision starts at `0` for
the first build of that day. `2026.10.28:0` is the first release build of 28 October 2026, and a
second, wrapper-only build the same day is `2026.10.28:1`, then `:2`, and so on.

ExVer is not SemVer. Its numeric portion takes any number of dot-separated components, and ExVer
**normalizes numeric leading zeros**, so write a single-digit month or day without a leading zero:
`2026.1.5`, never `2026.01.05`. The version string in `current.ts` and the git tag have to be the
same string, and `2026.10.28` has no leading zero to worry about.

## Applying the bump

The package version lives in `startos/versions/current.ts` and follows ExVer. Because the package
wraps our own application, there is no meaningful upstream portion to preserve; the date and the
revision are what move.

1. Edit `version` and `releaseNotes` in `startos/versions/current.ts` **in place**. Do not rename
   the file, do not rename the `current` export, and do not touch `startos/versions/index.ts`. A
   new version file is only spun off when the version already in `current.ts` carries a migration
   whose `up` body does work — see the Versions page of the packaging guide.
2. An application-only change needs no `Dockerfile` edit; the build picks the new source up from the
   repository root. A change to the set of application files needs the matching `COPY` line.
3. Write the release notes in every locale `current.ts` carries. They cover what changed since the
   version the registry last served, and they are the only place that tells the user about a step an
   update asks of them.
4. The git tag matches the version, with `:` replaced by `_` and a leading `v`: `2026.10.28:0`
   becomes `v2026.10.28_0`. Push the tag individually (`git push origin v2026.10.28_0`), not with
   `git push --tags`.

## Downgrading

A downgrade to an older package version is **not supported** once the application's schema has
moved forward: the older build refuses to open a database that is newer than the schema it knows,
rather than writing in it. Restore a backup taken with the older version, or reinstall and
configure the setup again.
