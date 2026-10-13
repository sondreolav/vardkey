import { i18n } from '../i18n'
import { sdk } from '../sdk'
import { dataMountpoint, imageId, volumeId } from '../utils'

const { InputSpec, Value } = sdk

// The key setup, the saved checks and the wallet software list cannot be
// recovered once they are gone, so the action takes a confirmation box and the
// handler refuses to run without it (section 31 point 2). A toggle has no
// `required` flag, so the confirmation is enforced in the handler.
const inputSpec = InputSpec.of({
  confirm: Value.toggle({
    name: i18n(
      'I confirm that the key setup, the saved checks and the wallet software list will be deleted and cannot be recovered',
    ),
    description: null,
    default: false,
  }),
})

const confirmationRequired = i18n(
  'The confirmation is required before the data can be deleted.',
)

export const deleteAllData = sdk.Action.withInput(
  // ID
  'delete-all-data',

  // Metadata
  async () => ({
    name: i18n('Delete all data'),
    description: i18n(
      'Delete the key setup, the saved checks and the wallet software list, so the app is back at the first-run setup step. The admin account is kept.',
    ),
    warning: null,
    allowedStatuses: 'any',
    group: null,
    visibility: 'enabled',
  }),

  inputSpec,

  // The box starts unticked, so the user confirms on every run.
  async () => ({ confirm: false }),

  // Handler
  async ({ effects, input }) => {
    if (!input.confirm) {
      throw new Error(confirmationRequired)
    }

    // maintenance.py needs the volume and nothing else: the image's own
    // DATABASE_PATH already points at /data/vardkey.sqlite3, which is where
    // the volume is mounted. A temporary subcontainer is used, because the
    // command is a one-off and not a daemon.
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
      'delete-all-data',
      async (sub) => {
        const result = await sub.exec([
          'python3',
          'maintenance.py',
          'delete-all-data',
        ])
        if (result.exitCode !== 0) {
          // exec() reports stdout and stderr as either text or bytes, so both
          // are normalised before they are used.
          const stderr = String(result.stderr).trim()
          throw new Error(stderr || i18n('The data could not be deleted.'))
        }
        report = String(result.stdout).trim()
      },
    )

    return {
      version: '1',
      title: i18n('Data deleted'),
      message: report,
      result: null,
    }
  },
)
