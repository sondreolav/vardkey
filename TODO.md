# TODO — Helsesjekk for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit fast **2-av-3 multisig-oppsett** med tre nøklar:

- Nøkkel 1: SeedSigner
- Nøkkel 2: Blockstream Jade
- Nøkkel 3: sky-nøkkel hos Nunchuk

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

Denne `TODO.md` er det einaste kravgrunnlaget du treng for MVP.

## Språkkrav

- [x] Brukargrensesnittet, app-tekst, kjeldekode, variabel- og funksjonsnamn, kommentarar og teknisk dokumentasjon skal vere på engelsk.
- [x] `TODO.md` kan vere på norsk; dette er det einaste unntaket.

---

# 1. Scope for første versjon

## Dette skal vere med

- [x] Ein enkel web-app med dashboard.
- [x] Registrering av dei tre nøklane.
- [x] Registrering av årleg health check.
- [x] Kontroll av alle punkta i den årlege sjekklista.
- [x] Varsel når eit kontrollpunkt krev oppfølging.
- [x] Historikk over gjennomførte health checks.
- [x] Automatisk forslag til neste sjekk, ca. eitt år fram i tid.
- [x] Rapporteksport i CSV-format.
- [x] Lokal SQLite-database.
- [ ] Persistent lagring på StartOS.
- [ ] StartOS health check.
- [ ] StartOS backup og restore.

## Dette skal ikkje vere med i første versjon

- [ ] Ingen AI-integrasjon i appen.
- [ ] Ingen Bitcoin-node-integrasjon.
- [ ] Ingen Bitcoin-signering.
- [ ] Ingen PSBT-generering eller signering.
- [ ] Ingen seed phrase-lagring.
- [ ] Ingen private key-lagring.
- [ ] Ingen cloud sync av appdata.
- [ ] Ingen ekstern database.
- [ ] Ingen PWA/offline-database.
- [ ] Ingen kalenderintegrasjon.
- [ ] Ingen avansert analyse eller grafar.
- [ ] Ingen støtte for fleire multisig-oppsett i MVP.

**Merk:** denne lista er eit varig forbod, ikkje ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- [x] Appen skal aldri spørje etter seed phrase.
- [x] Appen skal aldri spørje etter private keys.
- [x] Appen skal aldri lagre PIN, passord eller wallet-hemmeligheiter.
- [x] Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast i appen; berre om kontaktinfo er verifisert.
- [x] Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- [x] Appen skal vere lokal og enkel.
- [x] Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast i MVP.

---

# 3. Fast oppsett som appen skal støtte

Appen skal starte med eitt fast multisig-oppsett:

| Nøkkel | Type | Einheit |
|---|---|---|
| 1 | Hardware | SeedSigner |
| 2 | Hardware | Blockstream Jade |
| 3 | Cloud | Nunchuk |

- [x] Vis 2-av-3 som oppsettet i dashboardet.
- [x] Ha tre nøkkelprofilar, éin for kvar nøkkel.
- [ ] La brukaren gi nøklane lesbare namn dersom ønskjeleg. (Avgjort: ikkje no — faste namn er nok for MVP.)
- [x] Ikkje bygg generell støtte for mange oppsett enno.

---

# 4. Datamodell

Bruk SQLite med så få tabellar som mogleg.

**Merk:** §19 gjorde om datamodellen, §20 endra kva som blir spurt om i skjemaet, og §21 byter statusverdiar. Felta under er oppdaterte i tråd med alle tre.

## 4.1 `keys`

- [x] `id`
- [x] `key_number` = 1, 2 eller 3
- [x] `name`
- [x] `type` = `hardware` eller `cloud`
- [x] `device` = SeedSigner / Blockstream Jade / Nunchuk
- [x] `created_at`

## 4.2 `health_checks`

Ein rad/record for kvar innsending, som gjeld éin vald nøkkel (§19).

- [x] `id`
- [x] `checked_at`
- [x] `next_check_due`
- [x] `software_compatibility_status` — for nøkkel 3 utleidd frå `Availability` (§20); `IKKJE_VURDERT` blir `NOT_ASSESSED` i §21
- [x] `wallet_software` — vald programvare: `Sparrow Wallet` eller `Nunchuk` (§19)
- [x] `software_version` — versjonen til den valde programvara (§19)
- [x] `ai_security_status` — blir lagra per leverandør i `ai_security_checks`, jf. §6 steg 7 og §19
- [x] `contact_info_verified`
- [x] `comments`

**Endra i §19:** `sparrow_version` og `nunchuk_version` er tekne ut av kravet og erstatta av `wallet_software` og `software_version`. Kolonnane blir behaldne for gamle rader.

## 4.3 `key_checks`

Eitt record for den valde nøkkelen i kvar innsending.

- [x] `id`
- [x] `health_check_id`
- [x] `key_id`
- [x] `available`
- [x] `hardware_works`
- [x] `firmware_version`
- [x] `seed_backup_verified` — status `OK` eller `Problem`; gjeld nøkkel 1 og 2 (§19)
- [x] `cloud_health_status` — blir ikkje spurt om i skjemaet; utleidd frå `Availability` for nøkkel 3 (§20); `IKKJE_VURDERT` blir `NOT_ASSESSED` i §21
- [x] `cloud_provider_operational` — blir ikkje spurt om i skjemaet; utleidd frå `Availability` for nøkkel 3 (§20)
- [x] `address_path_verified` — status `OK` eller `Problem`; var Ja/Nei (§19)
- [x] `address_path`
- [x] `comments`

Reglar:

- [x] `hardware_works` skal vere relevant for nøkkel 1 og 2.
- [x] `firmware_version` skal vere relevant for nøkkel 1 og 2.
- [x] `seed_backup_verified` skal vere relevant for nøkkel 1 og 2, og ikkje for sky-nøkkelen.
- [x] `cloud_health_status` og `cloud_provider_operational` skal vere relevante for nøkkel 3.
- [x] `address_path` skal kunne lagre den verifiserte adressestien.
- [x] `seed_backup_verified` og `address_path_verified` skal berre ha verdiane `OK` eller `Problem`, og vere obligatoriske når `available` er Ja.
- [x] Når `available` er Nei, skal dei andre nøkkelfelta ikkje krevjast, og nøkkelnotatet skal framleis kunne fyllast ut (§19).
- [x] Når `available` er Nei for nøkkel 3, skal dei to cloud-felta likevel lagrast, utleidde som `PROBLEM` og `No` (§20).

**Endra i §19:** `seed_backup_status`, `address_verified` og `derivation_height` er tekne ut. Sjekkpunktet «Verifiser derivasjonshøgd» blir dekt av `address_path`.

## 4.4 `tool_checks`

Ein enkel matrise for støtte-kontrollen.

Produkta som skal vurderast, alle fire, men i ulike innsendingar (§19):

- SeedSigner
- Blockstream Jade
- Nunchuk
- Sparrow Wallet

Felt:

- [x] `id`
- [x] `health_check_id`
- [x] `product` — nøkkelproduktet pluss vald programvare, maks to rader per innsending (§19)
- [x] `bip327_status` — verdiane blir `YES` / `NO` / `NOT_ASSESSED` i §21
- [x] `slip39_status` — verdiane blir `YES` / `NO` / `NOT_ASSESSED` i §21

**Endra i §19:** `version`, `checked_at` og `notes` er tekne ut av kravet. Kolonnane blir behaldne for gamle rader.

---

# 5. Statusverdiar

## 5.1 Generelle kontrollar

Bruk enkle statusar som:

- `OK`
- `PROBLEM`
- `IKKJE_VURDERT`

- [x] Bruk same statuslogikk i database og UI.
- [x] Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.

**Endra i §21, ikkje implementert:** `IKKJE_VURDERT` blir bytt til `NOT_ASSESSED` på alle fire kolonnane som brukar han. Då er det ikkje norske ord att i koden; produktnamnet og databasefilnamnet blir dokumenterte som bevisste unntak.

## 5.2 KI-sikkerheitsstatus

Bruk nøyaktig desse fire verdiane:

- [x] `SECURE`
- [x] `PATCHED`
- [x] `VULNERABLE`
- [x] `COMPROMISED`

Ingen andre sikkerheitsstatusar skal brukast.

**Endra i §19:** dei norske verdiane `TRYGG`, `PATCHA`, `SÅRBAR` og `KOMPROMITTERT` er bytte ut med dei engelske. Eksisterande rader blir migrerte til dei nye verdiane.

---

# 6. Årleg health check — steg for steg

**Merk:** §19 gjer at éi innsending gjeld éin vald nøkkel, §20 gjer at nokre felt er skjulte og utleidde, og §21 endrar adressestifeltet og BIP327/SLIP39-statusane.

## Steg 1 — Start kontroll

- [x] Brukaren trykkjer `Start årleg health check`.
- [x] Brukaren vel kva nøkkel innsendinga gjeld: nøkkel 1, 2 eller 3 (§19).
- [x] Dagens dato blir føreslått automatisk.
- [x] Neste sjekkdato blir rekna ut på serveren som eitt kalenderår etter sjekkdatoen, og kan ikkje redigerast i skjemaet (§19).

## Steg 2 — Kontroller nøkkel 1: SeedSigner

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Hardware fungerer / fungerer ikkje.
- [x] Registrer firmware-versjon.
- [x] Kontroller seed-backup.
- [x] Kontroller at backupen er intakt og stemmer med hardware → `seed_backup_verified` (`OK` / `Problem`).
- [x] Verifiser adresse, derivasjonshøgd og adresse-sti → `address_path_verified` (`OK` / `Problem`) og `address_path` (tekst).
- [x] Kommentar ved behov.

**Endra i §21, ikkje implementert:** `Address path` blir berre vist når `Address path verified` er `OK`.

## Steg 3 — Kontroller nøkkel 2: Blockstream Jade

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Hardware fungerer / fungerer ikkje.
- [x] Registrer firmware-versjon.
- [x] Kontroller seed-backup.
- [x] Kontroller at backupen er intakt og stemmer med hardware → `seed_backup_verified` (`OK` / `Problem`).
- [x] Verifiser adresse, derivasjonshøgd og adresse-sti → `address_path_verified` (`OK` / `Problem`) og `address_path` (tekst).
- [x] Kommentar ved behov.

**Endra i §21, ikkje implementert:** `Address path` blir berre vist når `Address path verified` er `OK`.

## Steg 4 — Kontroller nøkkel 3: Nunchuk sky-nøkkel

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Gjennomfør cloud health check. (Endra i §20: feltet er fjerna frå skjemaet.)
- [x] Verifiser at Nunchuk framleis er i drift. (Endra i §20: feltet er fjerna frå skjemaet.)
- [x] Registrer resultatet av leverandør-kontrollen. (Endra i §20: blir utleidd frå `Availability`.)
- [x] Verifiser relevant adresse/oppsett → `address_path_verified` (`OK` / `Problem`) og `address_path` (tekst).
- [x] Kommentar ved behov.

**Endra i §20:** for nøkkel 3 dekkjer `Availability` både cloud-helsa og «leverandøren er i drift». Dei to felta er fjerna frå skjemaet og utleidde: `Availability` = Yes → `cloud_health_status` = `OK` og `cloud_provider_operational` = Yes; `Availability` = No → `PROBLEM` og `No`.

## Steg 5 — Programvare-kompatibilitet

- [x] Brukaren vel éi wallet-programvare: Sparrow Wallet eller Nunchuk (§19). For nøkkel 3 er valet låst til Nunchuk.
- [x] Registrer versjonen til den valde programvara i `software_version` (§19).
- [x] Verifiser at Sparrow og/eller Nunchuk støttar hardware-oppsettet.
- [x] Registrer `OK` eller `PROBLEM`.
- [x] Legg inn kommentar dersom det er problem.

**Endra i §19:** dei separate Sparrow- og Nunchuk-versjonsfelta er tekne ut.

**Endra i §20:** for nøkkel 3 blir kompatibilitetsfeltet skjult og utleidd: `Availability` = Yes → `OK`, `Availability` = No → `IKKJE_VURDERT`.

## Steg 6 — BIP327 / SLIP39

Registrer berre status for den valde nøkkelen sitt produkt og den valde programvara (§19):

- [x] Nøkkelproduktet: SeedSigner for nøkkel 1, Blockstream Jade for nøkkel 2, Nunchuk for nøkkel 3.
- [x] Vald programvare: Sparrow Wallet eller Nunchuk. Når Nunchuk både er nøkkel og programvare, blir det éi rad.

For kvart produkt:

- [x] Registrer `bip327_status`.
- [x] Registrer `slip39_status`.

Alle fire produkta skal framleis kunne registrerast, men i ulike innsendingar.

**Endra i §19:** «Version checked», «Date checked» og «Notes or source» er tekne ut.

**Endra i §21, ikkje implementert:** statusane blir `YES`, `NO` eller `NOT_ASSESSED`. `No` utløyser ikkje varsel i dag, sidan støtta for BIP327 og SLIP39 er liten.

## Steg 7 — KI-sikkerheitsstatus

Brukaren skal registrere resultat frå ein ekstern KI-/research-sjekk av leverandørane.

Leverandørar per innsending (§19):

- [x] Nøkkel 1: SeedSigner, Sparrow Wallet og Nunchuk.
- [x] Nøkkel 2: Blockstream Jade, Sparrow Wallet og Nunchuk.
- [x] Nøkkel 3: Nunchuk åleine.

For kvar leverandør:

- [x] Registrer status: `SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`.
- [x] Registrer kort kommentar.

Appen skal ikkje kontakte KI sjølv i MVP.

**Endra i §20:** for nøkkel 1 og 2 blir berre nøkkelproduktet og den valde programvara vist. Den tredje leverandøren blir skjult og får siste lagra status — men kjem tilbake av seg sjølv om han var `VULNERABLE` eller `COMPROMISED`.

## Steg 8 — Kontaktinfo

- [x] Stadfest at kontaktinformasjonen til alle nøkkelhaldarane er gyldig.
- [x] Lagre berre `JA` / `NEI`.
- [x] Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 9 — Kommentar

- [x] Eitt overordna kommentarfelt for observasjonar.
- [x] Eigne kommentarar per nøkkel der nødvendig.

## Steg 10 — Oppsummering

Før lagring skal appen vise:

- [x] Alle kontrollpunkt.
- [x] Alle problem.
- [x] Alle manglande kontrollar.
- [x] Neste sjekkdato.
- [x] Eventuelle handlingar som bør følgjast opp.
- [x] Utleidde og vidareførte verdiar, merkte som nettopp det (§20).

- [x] Brukaren må trykkje `Lagre health check` for å lagre kontrollen.

---

# 7. Varsel og oppfølging

Appen skal gi tydelege varsel når resultatet krev handling.

- [x] Nøkkel ikkje tilgjengeleg → vis at nøkkelen må bytast ut før du går vidare, og at resten av nøkkelfelta ikkje kan registrerast (§19). For nøkkel 3 blir dette eitt samanslått varsel (§20).
- [x] Hardware fungerer ikkje → vis at seed-backup bør testast på annan kompatibel hardware.
- [x] Seed-backup manglar eller er øydelagd → vis at PROTOKOLL 3: Nøkkeltap skal aktiverast. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Cloud-helse er `PROBLEM` eller leverandøren er ikkje i drift → vis at leverandørstatusen bør kontrollerast før du går vidare. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Adresseverifisering feilar → vis at adressa bør kontrollerast mot BSMS og testast på nytt. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Programvare støttar ikkje lenger hardware → vis at alternativ programvare/løysing bør vurderast.
- [x] BIP327-status er positiv → vis at framtidig BIP327-oppgradering kan vurderast.
- [x] SLIP39-status er positiv → vis at framtidig SLIP39-aktivering kan vurderast.
- [x] KI-status `VULNERABLE` → vis at firmware-/sikkerheitsproblem må følgjast opp.
- [x] KI-status `COMPROMISED` → vis at nøkkeltapsprosedyre må følgjast.
- [x] Kontaktinfo er ikkje stadfesta → vis at kontaktinformasjon må oppdaterast i den eksterne dokumentasjonen.

**Endra i §20:** når nøkkel 3 er utilgjengeleg, kjem det **eitt** samanslått kritisk varsel som nemner både at nøkkelen mangla og at leverandøren er registrert som nede. `cloud_provider_problem` held fram for rader der nøkkelen var tilgjengeleg (gamle rader).

Appen skal ikkje automatisk utføre nokon av desse tiltaka.

---

# 8. Dashboard

Dashboardet skal vere enkelt.

- [x] Vis 2-av-3 oppsettet.
- [x] Vis status for nøkkel 1.
- [x] Vis status for nøkkel 2.
- [x] Vis status for nøkkel 3.
- [x] Vis siste sjekk og neste forfall per nøkkel (§19: kvar nøkkel har sitt eige intervall).
- [x] Vis aktive varsel.
- [x] Knapp: `Start årleg health check`.
- [x] Knapp/lenke: `Historikk`.
- [x] Knapp/lenke: `Download CSV` (§10).

**Endra i §19, no implementert:** dei to oversiktskorta («Last completed» og «Next check») gjekk ut frå éin felles dato. Dei er no «Next check» (tidlegaste forfall blant nøklane, med kva nøkkel det gjeld) og «Attention» (kor mange nøklar som har passert fristen). Datoane per nøkkel står på nøkkelkorta, frå `GET /api/key-status`.

**Endra i §21, ikkje implementert:** framsida skal vise alle varsel frå alle lagra registreringar, ikkje berre den siste.

---

# 9. Historikk

- [x] Vis alle gjennomførte health checks kronologisk.
- [x] Opne ein health check i read-only-visning.
- [x] Vis kva nøkkel innsendinga gjeld (§19).
- [x] Vis dato.
- [x] Vis neste sjekk.
- [x] Vis status per nøkkel.
- [x] Vis programvarestatus — vald programvare og versjon (§19).
- [x] Vis BIP327/SLIP39-resultat.
- [x] Vis KI-status.
- [x] Vis kommentarar.
- [x] Gamle health checks skal ikkje overskrivast når ein ny blir registrert.

---

# 10. Rapporteksport

Eksporten skal vere **rein CSV**. Ingen XLSX-eksport.

- [x] Implementer CSV-eksport via `GET /api/export`. (Avgjort: CSV er nok, XLSX blir ikkje bygt.)
- [x] Éi rad per nøkkelsjekk, med ein kolonne for sjekk-id som knyter saman rader frå same innsending.
- [x] Eksporter alle nødvendige felt frå health check.
- [x] Éin gjennomført health check skal kunne identifiserast som éi historisk kontroll.
- [x] Ta med dato.
- [x] Ta med nøkkelstatus.
- [x] Ta med hardware-/firmware-resultat.
- [x] Ta med seed/cloud-resultat.
- [x] Ta med adresse-sti.
- [x] Ta med programvareversjon og kompatibilitet.
- [x] Ta med BIP327/SLIP39.
- [x] Ta med KI-status.
- [x] Ta med kontaktinfo-verifisering.
- [x] Ta med neste sjekk.
- [x] Ta med kommentarar.

**Endra:** kravet om Excel er teke ut. Filen er rein CSV (UTF-8, komma, CRLF, header). Han kan opnast i eit rekneark, men appen lovar ikkje Excel-kompatibilitet. Resultat som har meir enn éin verdi per innsending (BIP327, SLIP39 og KI-status) ligg i éi celle som `SeedSigner: OK; Sparrow Wallet: PROBLEM`.

**Endra i §21, ikkje implementert:** eksporten skal skrive dei nye statusverdiane (`YES` / `NO` / `NOT_ASSESSED`).

---

# 11. Backend

Vel den enklaste teknologien som passar godt for ein liten lokal web-app.

- [x] Implementer SQLite.
- [x] Implementer database-initialisering/migrering — må utvidast med migreringa i §19.
- [x] Implementer lagring av nøklar.
- [x] Implementer lagring av health checks — éi innsending gjeld éin vald nøkkel (§19).
- [x] Implementer historikk.
- [x] Implementer varsellogikken — varseltekstane og vilkåra blir endra i §19 og §20.
- [x] Implementer rapporteksport.
- [x] Implementer health endpoint.

Minimum:

- [x] `GET /health`
- [x] `GET /api/keys`
- [x] `GET /api/health-checks`
- [x] `GET /api/health-checks/:id`
- [x] `POST /api/health-checks` — kontrakten blir endra i §19.
- [x] `GET /api/export`

**Merk:** `GET /api/alerts`, `GET /api/key-status` og `GET /api/previous-values` er ekstra endepunkt utanom minimumslista, fordi dashboardet og skjemaet treng dei. Dei står ikkje i spesifikasjonen enno.

**Endra i §21, ikkje implementert:** `GET /api/alerts` skal summere alle lagra kontrollar, gje kvart varsel `check_id` og `checked_at`, og slå saman like varsel så berre den nyaste viser.

---

# 12. Frontend

- [x] Lag enkel responsiv web-UI.
- [x] Prioriter enkelheit framfor grafisk kompleksitet.
- [x] Bruk tydelege statusfelt.
- [x] Bruk faste val der status skal vere ein avgrensa verdi.
- [x] Vis problem tydeleg.
- [x] Vis kva som står att før ein health check kan lagrast.
- [ ] Sørg for at appen fungerer godt i vanleg StartOS-browser.

**Endra i §21, ikkje implementert:** `Address path` blir berre vist når `Address path verified` er `OK`, og framsida viser alle varsel.

---

# 13. StartOS 0.4.0

Bygg appen som éin enkel StartOS-service.

```text
StartOS 0.4.0
└── Helsesjekk
    ├── Web UI
    ├── Backend/API
    ├── SQLite
    └── Persistent data
```

- [ ] Opprett StartOS package.
- [ ] Opprett manifest.
- [ ] Opprett service-definisjon.
- [ ] Opprett HTTP web-interface.
- [ ] Opprett persistent volume.
- [ ] Opprett health check.
- [ ] Opprett backup-oppsett.
- [ ] Opprett installasjons-/brukarinstruksjonar.
- [ ] Bygg `.s9pk`.
- [ ] Verifiser at pakken kan installerast på StartOS 0.4.0.

Unngå:

- [ ] Ingen Postgres.
- [ ] Ingen Redis.
- [ ] Ingen ekstern backend.
- [ ] Ingen ekstern cloud-service for appdata.
- [ ] Ingen ekstra container utan konkret behov.

**Merk:** denne lista er eit varig forbod, ikkje ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

---

# 14. Lagring og backup

- [ ] SQLite-database skal liggje på persistent volum.
- [ ] Appdata skal overleve restart.
- [ ] Konfigurer StartOS backup av persistent data.
- [ ] Test backup.
- [ ] Test restore.
- [ ] Verifiser at gamle health checks finst etter restore.

---

# 15. Sikkerheit og personvern

- [x] Ingen seed phrase i database.
- [x] Ingen private keys i database.
- [x] Ingen wallet-passord i database.
- [x] Ingen sky-passord eller tokens i database.
- [x] Ingen unødvendige personopplysningar.
- [x] Kontaktinfo blir berre registrert som verifisert/ikkje verifisert.
- [x] Valider input på serveren.
- [x] Bruk parameteriserte SQL-spørringar.
- [x] Ikkje implementer eigen kryptografi.
- [x] Ikkje send data til eksterne tenester i MVP.

---

# 16. Testing

## Funksjonstest

- [ ] Opprett dei tre nøklane.
- [ ] Start health check.
- [ ] Fullfør alle kontrollpunkt.
- [ ] Lagre health check.
- [ ] Vis han i historikken.
- [ ] Start ny health check.
- [ ] Verifiser at gammal kontroll framleis finst.

## Problemtest

- [ ] Test nøkkel utilgjengeleg.
- [ ] Test hardware-feil.
- [ ] Test seed-backup-feil.
- [ ] Test adresseverifiseringsfeil.
- [ ] Test programvare-inkompatibilitet.
- [ ] Test BIP327-resultat.
- [ ] Test SLIP39-resultat.
- [ ] Test KI-status `VULNERABLE`.
- [ ] Test KI-status `COMPROMISED`.
- [ ] Test kontaktinfo `NEI`.

## StartOS-test

- [ ] Installer `.s9pk` på StartOS 0.4.0.
- [ ] Start service.
- [ ] Opne web UI.
- [ ] Utfør ein komplett test-check.
- [ ] Restart service.
- [ ] Verifiser at data framleis finst.
- [ ] Ta backup.
- [ ] Restore backup.
- [ ] Verifiser data etter restore.

---

# 17. Ferdigkriterium for første release

Før første release skal alle desse vere oppfylte:

- [ ] Appen køyrer på StartOS 0.4.0.
- [ ] Dei tre nøklane er representerte i appen.
- [ ] Ein komplett årleg health check kan gjennomførast i nettlesaren.
- [ ] Alle årlege kontrollpunkt kan registrerast.
- [ ] BIP327/SLIP39 kan registrerast for SeedSigner, Blockstream Jade, Nunchuk og Sparrow.
- [ ] KI-status kan registrerast som SECURE, PATCHED, VULNERABLE eller COMPROMISED.
- [ ] Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- [ ] Problem gir tydelege varsel.
- [ ] Neste sjekk blir lagra.
- [ ] Historikk fungerer.
- [ ] CSV-rapport kan eksporterast.
- [ ] Data overlever restart.
- [ ] Backup og restore fungerer.
- [ ] Ingen wallet-hemmeligheiter blir lagra.

**Endra:** punktet om Excel-kompatibel rapport er bytt til CSV-rapport, jf. §10.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- [x] 1. Opprett grunnleggande web-app.
- [x] 2. Opprett SQLite og datamodellen.
- [x] 3. Implementer dei tre faste nøklane.
- [ ] 4. Implementer health check-skjemaet.
- [x] 5. Implementer lagring og historikk.
- [ ] 6. Implementer varsellogikken.
- [x] 7. Implementer dashboard.
- [x] 8. Implementer rapporteksport.
- [ ] 9. Implementer StartOS package.
- [ ] 10. Implementer persistent storage og backup.
- [ ] 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** steg 4, 5 og 6 vart først fullførte før §19 vart vedteken. Dei vart sette tilbake til uticka og gjort på nytt i tråd med §19. Steg 7 og 8 er gjorde etter §19. Steg 4 og 6 er framleis uticka fordi §20 og §21 endrar delar av dei. 87 grøne testar.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19. Ny avgjerd: registrering per nøkkel

Denne delen er den nyaste avgjerda og overstyrer motstridande krav ovanfor om at alle nøklane eller alle produkta må registrerast i same innsending. Eksisterande historiske data skal bevarast.

**Status:** implementert og verifisert.

## Kvar innsending

- [x] Ei innsending skal registrere kontrollen av éin vald nøkkel, ikkje alle tre samtidig.
- [x] Brukaren skal velje nøkkel 1 (SeedSigner), nøkkel 2 (Blockstream Jade) eller nøkkel 3 (Nunchuk).
- [x] Alle nøkkelkontrollar og nøkkelnotat i innsendinga skal gjelde berre den valde nøkkelen.
- [x] Brukaren vel sjekkdato. Neste sjekkdato skal automatisk vere eitt kalenderår etter sjekkdatoen, skal ikkje vere redigerbar i skjemaet, og skal reknast/validerast på serveren.
- [x] Kontaktstadfesting og overordna kommentar skal framleis kunne registrerast per innsending.

## Programvarekompatibilitet

- [x] Brukaren skal velje éi wallet-programvare: Sparrow eller Nunchuk.
- [x] Registrer kompatibilitetsstatus og versjonen til den valde programvara for den valde nøkkelen.
- [x] Fjern dei separate Sparrow- og Nunchuk-versjonsfelta.

## BIP327 / SLIP39

- [x] Registrer berre BIP327-status og SLIP39-status for den valde nøkkelen/produktet i kvar innsending.
- [x] Fjern «Version checked», «Date checked» og «Notes or source» frå denne delen.
- [x] Ikkje krev status for dei andre nøklane/produkta i same innsending.

## Security status

- [x] SeedSigner-status skal berre følgje registreringar av nøkkel 1.
- [x] Blockstream Jade-status skal berre følgje registreringar av nøkkel 2.
- [x] Nunchuk- og Sparrow-status skal følgje kvar registrering, sidan dei også er wallet-programvare.
- [x] Ha berre éin Nunchuk-status per innsending. Ved nøkkel 3 gjeld den statusen Nunchuk-programvara og Nunchuk-nøkkelen; ikkje lag to dupliserte statusfelt.
- [x] Vis og krev berre security status-felt som er relevante for vald nøkkel og programvare. Ikkje krev status for alle tre nøklane i éi innsending.

**Endra i §20:** for nøkkel 1 og 2 blir leverandøren som ikkje er vald skjult og vidareført, i staden for å bli vist kvar gong. Sjå §20.

## Lagring, historikk og verifikasjon

- [x] Knytt nøkkelsjekk, programvarekompatibilitet, BIP327/SLIP39 og relevante security status-resultat til same innsending og vald nøkkel.
- [x] Oppdater historikkdetaljen slik at han tydeleg viser vald nøkkel og tilhøyrande resultat.
- [x] Bevar eksisterande lagra registreringar; bruk trygg, bakoverkompatibel databasemigrering dersom datamodellen må endrast.
- [x] Oppdater servervalidering og testar: ei innsending skal krevje éin konfigurert nøkkel og gyldige, relevante resultat, og avvise manglande eller dupliserte nøkkel-/produktregistreringar og ugyldige programvareval.
- [x] Test registrering av kvar nøkkel, automatisk neste dato, relevante programvare- og security status-resultat, og at eldre historikk framleis kan lesast.

---

# 20. Ny avgjerd: skjulte felt som blir utleidde eller vidareførte

Vedteken etter at steg 8 var ferdig. Endra delar av §4.2, §4.3, §6 (steg 4, 5, 7 og 10), §7, §11 og §19.

**Status:** implementert og verifisert (87 grøne testar).

## Nøkkel 3: `Availability` dekkjer cloud-kontrollen

- [x] Berre `Availability` skal visast av nøkkelfelta for nøkkel 3.
- [x] `Cloud health check` og `Provider operational` skal fjernast frå skjemaet og utleiast: `Availability` = Yes → `cloud_health_status` = `OK` og `cloud_provider_operational` = 1; `Availability` = No → `PROBLEM` og 0.
- [x] `Availability` ubesvart → begge felta tomme, som i dag.
- [x] `Software compatibility` skal skjulast for nøkkel 3 og utleiast: `Availability` = Yes → `OK`, `Availability` = No → `IKKJE_VURDERT`.
- [x] Kolonnane `cloud_health_status`, `cloud_provider_operational` og `software_compatibility_status` skal behaldast for gamle rader.
- [x] Servervalidering skal behalde dei utleidde cloud-verdiane for nøkkel 3 når `available` er 0 (i dag blir dei tømde).

## Security status følgjer programvarevalet

- [x] For nøkkel 1 og 2 skal `Security status` berre vise nøkkelproduktet og den valde programvara.
- [x] Den tredje leverandøren skal skjulast og få siste lagra status for den leverandøren.
- [x] Er den siste statusen `VULNERABLE` eller `COMPROMISED`, skal feltet visast likevel.
- [x] Har leverandøren ingen tidlegare status, skal han starte som `SECURE`.
- [x] Dei skjulte verdiane skal framleis sendast inn, slik at POST-kontrakten, historikken og eksporten er uendra.

## Placeholder og innsyn

- [x] `Firmware version` og `Address path` skal vise førre lagra verdi som placeholder.
- [x] `Software version` skal vise førre verdi berre når same programvare er vald no.
- [x] Alle utleidde og vidareførte verdiar skal listast i Review-oppsummeringa, merkte som utleidde eller vidareførte.

## Varsel

- [x] Når nøkkel 3 er utilgjengeleg, skal det kome **eitt** samanslått kritisk varsel: «This key was not available and the cloud provider is recorded as not operating. Check the provider status and replace the key before continuing; the remaining checks for this key cannot be recorded.»
- [x] `cloud_provider_problem` skal framleis gjelde rader der nøkkelen var tilgjengeleg (gamle rader).

## Følgje å vite om

- [x] Nøkkel 3 kan ikkje lenger gi varselet `software_incompatible`, sidan kompatibilitetsstatusen blir utleidd til `OK` eller `IKKJE_VURDERT`.

---

# 21. Ny avgjerd: engelske statusverdiar, adressesti og alle varsel

Vedteken etter at §20 var ferdig. Endrar delar av §4.2, §4.3, §4.4, §5.1, §6 (steg 2, 3 og 6), §7, §8, §10, §11 og §12.

**Ingenting av dette er implementert enno.**

## Engelske statusverdiar

- [ ] `IKKJE_VURDERT` skal bytast til `NOT_ASSESSED` på alle fire kolonnane som brukar han: `health_checks.software_compatibility_status`, `key_checks.cloud_health_status`, `tool_checks.bip327_status` og `tool_checks.slip39_status`.
- [ ] BIP327- og SLIP39-statusane skal ha verdiane `YES`, `NO` eller `NOT_ASSESSED` i staden for `OK`, `PROBLEM` og `IKKJE_VURDERT`.
- [ ] Migreringa skal mappe gamle rader: `OK` → `YES`, `PROBLEM` → `NO`, `IKKJE_VURDERT` → `NOT_ASSESSED`.
- [ ] Skjemaval, validering, varsel, CSV-eksport og testar skal bruke dei nye verdiane.
- [ ] Produktnamnet «Helsesjekk» og databasefilnamnet `data/helsesjekk.sqlite3` skal behaldast, og dokumenterast som bevisste unntak frå engelskregelen.

## Adressesti blir vist etter behov

- [ ] `Address path` skal berre visast når `Address path verified` er `OK`, og skjulast når han er `Problem` eller ikkje svara.

## Alle varsel på framsida

- [ ] `GET /api/alerts` skal summere varsla frå alle lagra kontrollar, ikkje berre den siste.
- [ ] Kvart varsel skal ha med `check_id` og `checked_at`, slik at ein ser kva registrering det kjem frå.
- [ ] Like varsel (same `code` og `source`) skal slåast saman, og berre den nyaste skal visast, med datoen sin.
- [ ] Varsla skal listast med dei kritiske først, og deretter nyaste først.
- [ ] Framsida skal vise alle varsla som kjem frå endepunktet.

## Framtidig arbeid, ikkje no

- [ ] Varsel om at oppsettet kan oppgraderast når alle nøklar og all programvare svarar `YES` på anten BIP327 eller SLIP39. Krev at appen ser på tvers av alle registreringar.
- [ ] Ein måte å lukke eller kvittere ut varsel på.

**Teknisk merknad:** endringane i statusverdiane rører `CHECK`-reglane på `health_checks`, `key_checks` og `tool_checks`, og `health_checks` er ein foreldretabell med framandnøklar frå dei tre andre tabellane. Migreringa må difor slå `PRAGMA foreign_keys` av før transaksjonen, slå han på att etterpå og køyre `PRAGMA foreign_key_check`. Skjemaet går til versjon 6.
