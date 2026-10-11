import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.1.0:0',
  releaseNotes: {
    en_US:
      'Initial StartOS package for VardKey. The service runs one daemon with the web interface, and keeps its SQLite database on the persistent "main" volume.',
    es_ES:
      'Paquete inicial de StartOS para VardKey. El servicio ejecuta un solo demonio con la interfaz web y guarda su base de datos SQLite en el volumen persistente "main".',
    de_DE:
      'Erstes StartOS-Paket für VardKey. Der Dienst läuft mit einem einzigen Daemon samt Weboberfläche und hält seine SQLite-Datenbank auf dem persistenten Volume "main".',
    pl_PL:
      'Pierwszy pakiet StartOS dla VardKey. Usługa uruchamia jeden demon z interfejsem webowym i przechowuje bazę SQLite na trwałym wolumenie "main".',
    fr_FR:
      'Premier paquet StartOS pour VardKey. Le service exécute un seul démon avec l’interface web et conserve sa base SQLite sur le volume persistant « main ».',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
