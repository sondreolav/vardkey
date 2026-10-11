import { sdk } from './sdk'

// Back up the "main" volume, which holds the SQLite database. StartOS stops the
// service for the duration of a backup (and restarts it afterwards only if it
// was running), so the database file is quiescent while it is copied and no
// separate snapshot hook is needed. See README.md — Backups and Restore.
export const { createBackup, restoreInit } = sdk.setupBackups(
  async ({ effects }) => sdk.Backups.ofVolumes('main'),
)
