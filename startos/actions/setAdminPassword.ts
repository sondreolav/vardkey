import { i18n } from '../i18n'
import { sdk } from '../sdk'
import { dataMountpoint, imageId, volumeId } from '../utils'

const { InputSpec, Value } = sdk

// The admin password is generated inside the container, never passed into it.
// The SDK documents no way to feed stdin to a `withTemp` command, and an
// argument would be visible in the process list, so maintenance.py generates the
// password and prints the credentials as one JSON object that the handler reads
// back. That is the packaging guide's own password-reset pattern
// (section 31 point 1).
const inputSpec = InputSpec.of({
  username: Value.text({
    name: i18n('Admin username'),
    description: i18n(
      'Leave blank to keep the current username, or to create the admin account when none exists.',
    ),
    required: false,
    default: null,
    patterns: [
      {
        regex: '.{1,60}',
        description: i18n('Use at most 60 characters.'),
      },
    ],
  }),
})

export const setAdminPassword = sdk.Action.withInput(
  // ID
  'set-admin-password',

  // Metadata. The form is the confirmation, so no separate warning is needed.
  {
    name: i18n('Set Admin Password'),
    description: i18n(
      'Generate a new admin password and show it once. Replaces any existing password.',
    ),
    warning: null,
    allowedStatuses: 'any',
    group: null,
    visibility: 'enabled',
  },

  inputSpec,

  // The username cannot be read from the database from here, so the field
  // starts empty and the command keeps the stored username.
  async () => ({ username: null }),

  // Handler
  async ({ effects, input }) => {
    // The image's own DATABASE_PATH already points at /data/vardkey.sqlite3,
    // which is where the volume is mounted. A temporary subcontainer is used,
    // because the command is a one-off and not a daemon.
    const mounts = sdk.Mounts.of().mountVolume({
      volumeId,
      subpath: null,
      mountpoint: dataMountpoint,
      readonly: false,
    })

    let report = ''
    await sdk.SubContainer.withTemp(
      effects,
      { imageId },
      mounts,
      'set-admin-password',
      async (sub) => {
        // The username is not a secret, so it may travel as an argument. The
        // password is generated in the container and never passed in at all.
        const command = ['python3', 'maintenance.py', 'set-admin-password']
        const username = (input.username ?? '').trim()
        if (username) {
          command.push('--username', username)
        }
        const result = await sub.exec(command)
        if (result.exitCode !== 0) {
          const stderr = String(result.stderr).trim()
          throw new Error(stderr || i18n('The admin password could not be set.'))
        }
        report = String(result.stdout).trim()
      },
    )

    let username = ''
    let password = ''
    try {
      const credentials = JSON.parse(report)
      username = String(credentials.username ?? '')
      password = String(credentials.password ?? '')
    } catch {
      throw new Error(i18n('The admin password could not be read back.'))
    }

    return {
      version: '1',
      title: i18n('Admin credentials'),
      message: i18n(
        'Sign in to VardKey with these credentials. The password is shown once, so store it somewhere safe.',
      ),
      result: {
        type: 'group',
        value: [
          {
            type: 'single',
            name: i18n('Username'),
            description: null,
            value: username,
            masked: false,
            copyable: true,
            qr: false,
            launchable: false,
          },
          {
            type: 'single',
            name: i18n('Password'),
            description: null,
            value: password,
            masked: true,
            copyable: true,
            qr: false,
            launchable: false,
          },
        ],
      },
    }
  },
)
