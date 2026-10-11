// Constants shared by the package's manifest, daemon, interface, and backups.
// The internal port must be the same everywhere: app.py reads PORT, main.ts
// passes it, and interfaces.ts binds it. Changing one alone leaves the
// readiness check permanently red.

export const imageId = 'main'
export const volumeId = 'main'
export const subcontainerName = 'vardkey-sub'

// The application listens on this port inside the container.
export const uiPort = 8080

// The SQLite database lives on the persistent "main" volume, which main.ts
// mounts at /data.
export const dataMountpoint = '/data'
export const databasePath = '/data/vardkey.sqlite3'
