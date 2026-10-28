import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '2026.10.28:1',
  releaseNotes: {
    en_US:
      'The links a user sees now point at the public GitHub mirror. The package repository and the upstream repository in the manifest, and the repository links in the README and the instructions, point at https://github.com/sondreolav/vardkey instead of the self-hosted instance development happens on. No application change: the same code, the same schema, the same database, and nothing to do after updating.',
    es_ES:
      'Los enlaces que ve el usuario ahora apuntan al espejo público de GitHub. El repositorio del paquete y el repositorio de origen en el manifiesto, y los enlaces al repositorio en el README y en las instrucciones, apuntan a https://github.com/sondreolav/vardkey en lugar de la instancia autoalojada donde se desarrolla. Sin cambios en la aplicación: el mismo código, el mismo esquema, la misma base de datos, y nada que hacer tras actualizar.',
    de_DE:
      'Die Links, die der Benutzer sieht, zeigen jetzt auf den öffentlichen GitHub-Spiegel. Das Paket-Repository und das Upstream-Repository im Manifest sowie die Repository-Links in der README und in der Anleitung zeigen auf https://github.com/sondreolav/vardkey statt auf die selbst gehostete Instanz, auf der entwickelt wird. Keine Änderung an der Anwendung: derselbe Code, dasselbe Schema, dieselbe Datenbank, und nach dem Update ist nichts zu tun.',
    pl_PL:
      'Widoczne dla użytkownika odnośniki wskazują teraz na publiczny mirro GitHub. Repozytorium pakietu i repozytorium źródłowe w manifeście oraz odnośniki do repozytorium w README i w instrukcji wskazują na https://github.com/sondreolav/vardkey zamiast na samodzielnie hostowaną instancję, na której trwa rozwój. Bez zmian w aplikacji: ten sam kod, ten sam schemat, ta sama baza danych i nic do zrobienia po aktualizacji.',
    fr_FR:
      'Les liens visibles par l’utilisateur pointent désormais vers le miroir public GitHub. Le dépôt du paquet et le dépôt amont dans le manifeste, ainsi que les liens vers le dépôt dans le README et dans les instructions, pointent vers https://github.com/sondreolav/vardkey au lieu de l’instance auto-hébergée où le développement a lieu. Aucun changement dans l’application : le même code, le même schéma, la même base de données, et rien à faire après la mise à jour.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
