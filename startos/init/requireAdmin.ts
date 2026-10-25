import { i18n } from '../i18n'
import { sdk } from '../sdk'
import { setAdminPassword } from '../actions/setAdminPassword'
import { databasePath, dataMountpoint, imageId, volumeId } from '../utils'

// `createTask()` resolves to null, so the replay id cannot be read back from
// it. It is written once here, and the same string is used to clear the task,
// so the task raised at one init is the task cleared at the next. StartOS
// offers no condition of its own for "the admin password is unset": the only
// TaskCondition in this SDK release is 'input-not-matches', which is about an
// action's form (section 32.8 point 1).
const ADMIN_TASK_REPLAY_ID = 'vardkey:set-admin-password'

// The package cannot read the app's SQLite database from its own JavaScript
// context, so this probe runs inside a temporary subcontainer. It only reads,
// and a database that does not exist yet - a fresh install - answers "no".
//
// The task itself points at the existing `set-admin-password` action, which
// runs `maintenance.py set-admin-password` in a `withTemp` subcontainer and
// generates the password *inside* it. Nothing travels from the host into the
// container, as an argument or on stdin (section 32.8 point 1).
const ADMIN_PROBE = `
import sqlite3
try:
    db = sqlite3.connect("file:${databasePath}?mode=ro", uri=True)
    row = db.execute(
        "select value from app_settings where name = ?",
        ("admin_password_hash",),
    ).fetchone()
    print("yes" if row and row[0] else "no")
except Exception:
    print("no")
`

/**
 * Keep a required task raised while the service has no admin account.
 *
 * VardKey is unusable without an admin, and its own login gate already refuses
 * everything until one exists: `/api/*` answers 401, the pages redirect to
 * `/login`, and `/login` shows the create-admin form. This init script adds the
 * packaging half of that rule, so the user is asked to set the password from
 * StartOS instead of being left on a login page. The task points at the
 * existing `Set Admin Password` action, so the password is still generated
 * inside the container and shown once.
 *
 * The probe fails open. If it cannot run, no task is raised rather than a task
 * being raised on a guess, because a task that is raised wrongly would hold the
 * service back for a user who already has an admin account.
 */
export const requireAdmin = sdk.setupOnInit(async (effects) => {
  const mounts = sdk.Mounts.of().mountVolume({
    volumeId,
    subpath: null,
    mountpoint: dataMountpoint,
    readonly: true,
  })

  // True unless the probe answers "no": an unreadable database, a missing
  // python or an image that is not ready yet must never block the service.
  let configured = true
  try {
    await sdk.SubContainer.withTemp(
      effects,
      { imageId },
      mounts,
      'admin-configured',
      async (sub) => {
        const result = await sub.exec(['python3', '-c', ADMIN_PROBE])
        if (result.exitCode === 0) {
          configured = String(result.stdout).trim() === 'yes'
        }
      },
    )
  } catch (error) {
    // A caught value is `unknown`, so it is normalised before it is used, the
    // same way the two actions normalise stdout and stderr.
    console.warn(
      `The admin probe did not run, so it was ignored: ${String(error)}`,
    )
  }

  if (configured) {
    return sdk.action.clearTask(effects, ADMIN_TASK_REPLAY_ID)
  }

  await sdk.action.createOwnTask(effects, setAdminPassword, 'important', {
    reason: i18n('Set the admin password before VardKey can be used.'),
    replayId: ADMIN_TASK_REPLAY_ID,
  })
})
