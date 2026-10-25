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

## Applying the bump

The package version lives in `startos/versions/current.ts` and follows ExVer. Because the package
wraps our own application, there is no meaningful upstream portion to preserve; the downstream
revision is what moves.

1. Decide the new version. Use `0.1.0:1`, `0.1.0:2`, … for wrapper-only changes, and `1.0.0:0` when
   the package reaches its first release (`TODO.md` section 30).
2. Edit `version` and `releaseNotes` in `startos/versions/current.ts` **in place**. Do not rename
   the file, do not rename the `current` export, and do not touch `startos/versions/index.ts`. A
   new version file is only spun off when the version already in `current.ts` carries a migration
   whose `up` body does work — see the Versions page of the packaging guide.
3. An application-only change needs no `Dockerfile` edit; the build picks the new source up from
   the repository root. A change to the set of application files needs the matching `COPY` line.
4. The git tag matches the version, with `:` replaced by `_` and a leading `v`: `0.1.0:1` becomes
   `v0.1.0_1`. Push the tag individually.

## Downgrading

A downgrade to an older package version is **not supported** once the application's schema has
moved forward: the older build refuses to open a database that is newer than the schema it knows,
rather than writing in it. Restore a backup taken with the older version, or reinstall and
configure the setup again.
