import { i18n } from '../i18n'
import { sdk } from '../sdk'
import { dataMountpoint, imageId, volumeId } from '../utils'

const { InputSpec, Value } = sdk

// The history cannot be recovered once it is gone, so the action takes a
// confirmation box, and the handler refuses to run without it (section 31
// point 2). A toggle has no `required` flag, so the confirmation is enforced in
// the handler.
const inputSpec = InputSpec.of({
  confirm: Value.toggle({
    name: i18n('I confirm that the stored history will be deleted and cannot be recovered'),
    description: null,
    default: false,
  }),
})

export const deleteHistory = sdk.Action.withInput(
  // ID
  'delete-history',

  // Metadata
  async () => ({
    name: i18n('Delete history'),
    description: i18n('Delete every saved health check, with the follow-up it closed. The key setup and the wallet software list are kept.'),
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
      throw new Error(i18n('The confirmation is required before the history can be deleted.'))
    }

    // maintenance.py needs the volume and nothing else: the image's own
    // DATABASE_PATH already points at /data/vardkey.sqlite3, which is where the
    // volume is mounted. A temporary subcontainer is used because the command
    // is a one-off, not a daemon.
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
      'delete-history',
      async (sub) => {
        const result = await sub.exec(['python3', 'maintenance.py', 'delete-history'])
        if (result.exitCode !== 0) {
          // exec() returns stdout/stderr as either text or bytes, so both are
          // normalised before they are used.
          const stderr = String(result.stderr).trim()
          throw new Error(stderr || i18n('The history could not be deleted.'))
        }
        report = String(result.stdout).trim()
      },
    )

    return {
      version: '1',
      title: i18n('History deleted'),
      message: report,
      result: null,
    }
  },
)
