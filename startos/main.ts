import { i18n } from './i18n'
import { sdk } from './sdk'
import {
  dataMountpoint,
  databasePath,
  imageId,
  subcontainerName,
  uiPort,
  volumeId,
} from './utils'

export const main = sdk.setupMain(async ({ effects }) => {
  /**
   * ======================== Setup (optional) ========================
   *
   * Fetch any resources or run any preliminary commands here.
   */
  console.info(i18n('Starting VardKey'))

  /**
   * ======================== Daemons ========================
   *
   * VardKey is a single daemon: one container, one process, and one SQLite
   * database on the persistent "main" volume.
   */
  return sdk.Daemons.of(effects).addDaemon('primary', {
    subcontainer: sdk.SubContainer.of(
      effects,
      { imageId },
      sdk.Mounts.of().mountVolume({
        volumeId,
        subpath: null,
        mountpoint: dataMountpoint,
        readonly: false,
      }),
      subcontainerName,
    ),
    exec: {
      command: ['python3', 'app.py'],
      env: {
        PORT: String(uiPort),
        DATABASE_PATH: databasePath,
      },
    },
    ready: {
      display: i18n('Web Interface'),
      // checkWebUrl against the app's own /health endpoint. The port here must
      // match uiPort and the port bound in interfaces.ts, or the check never
      // goes green.
      fn: () =>
        sdk.healthCheck.checkWebUrl(
          effects,
          `http://127.0.0.1:${uiPort}/health`,
          {
            successMessage: i18n('The web interface is ready'),
            errorMessage: i18n('The web interface is not ready'),
          },
        ),
    },
    requires: [],
  })
})
