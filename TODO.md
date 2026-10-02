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
- [ ] Rapporteksport i Excel-kompatibelt format.
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

**Merk:** §19 gjorde om datamodellen. Felta under er oppdaterte i tråd med §19 og er no implementerte.

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
- [x] `software_compatibility_status`
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
- [x] `cloud_health_status`
- [x] `cloud_provider_operational`
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
- [x] `bip327_status`
- [x] `slip39_status`

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

**Merk:** §19 gjer at éi innsending gjeld éin vald nøkkel.

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

## Steg 3 — Kontroller nøkkel 2: Blockstream Jade

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Hardware fungerer / fungerer ikkje.
- [x] Registrer firmware-versjon.
- [x] Kontroller seed-backup.
- [x] Kontroller at backupen er intakt og stemmer med hardware → `seed_backup_verified` (`OK` / `Problem`).
- [x] Verifiser adresse, derivasjonshøgd og adresse-sti → `address_path_verified` (`OK` / `Problem`) og `address_path` (tekst).
- [x] Kommentar ved behov.

## Steg 4 — Kontroller nøkkel 3: Nunchuk sky-nøkkel

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Gjennomfør cloud health check.
- [x] Verifiser at Nunchuk framleis er i drift.
- [x] Registrer resultatet av leverandør-kontrollen.
- [x] Verifiser relevant adresse/oppsett → `address_path_verified` (`OK` / `Problem`) og `address_path` (tekst).
- [x] Kommentar ved behov.

## Steg 5 — Programvare-kompatibilitet

- [x] Brukaren vel éi wallet-programvare: Sparrow Wallet eller Nunchuk (§19). For nøkkel 3 er valet låst til Nunchuk.
- [x] Registrer versjonen til den valde programvara i `software_version` (§19).
- [x] Verifiser at Sparrow og/eller Nunchuk støttar hardware-oppsettet.
- [x] Registrer `OK` eller `PROBLEM`.
- [x] Legg inn kommentar dersom det er problem.

**Endra i §19:** dei separate Sparrow- og Nunchuk-versjonsfelta er tekne ut.

## Steg 6 — BIP327 / SLIP39

Registrer berre status for den valde nøkkelen sitt produkt og den valde programvara (§19):

- [x] Nøkkelproduktet: SeedSigner for nøkkel 1, Blockstream Jade for nøkkel 2, Nunchuk for nøkkel 3.
- [x] Vald programvare: Sparrow Wallet eller Nunchuk. Når Nunchuk både er nøkkel og programvare, blir det éi rad.

For kvart produkt:

- [x] Registrer `bip327_status`.
- [x] Registrer `slip39_status`.

Alle fire produkta skal framleis kunne registrerast, men i ulike innsendingar.

**Endra i §19:** «Version checked», «Date checked» og «Notes or source» er tekne ut.

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

- [x] Brukaren må trykkje `Lagre health check` for å lagre kontrollen.

---

# 7. Varsel og oppfølging

Appen skal gi tydelege varsel når resultatet krev handling.

- [x] Nøkkel ikkje tilgjengeleg → vis at nøkkelen må bytast ut før du går vidare, og at resten av nøkkelfelta ikkje kan registrerast (§19).
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

Appen skal ikkje automatisk utføre nokon av desse tiltaka.

---

# 8. Dashboard

Dashboardet skal vere enkelt.

- [x] Vis 2-av-3 oppsettet.
- [ ] Vis status for nøkkel 1.
- [ ] Vis status for nøkkel 2.
- [ ] Vis status for nøkkel 3.
- [ ] Vis siste sjekk og neste forfall per nøkkel (§19: kvar nøkkel har sitt eige intervall).
- [x] Vis aktive varsel.
- [x] Knapp: `Start årleg health check`.
- [x] Knapp/lenke: `Historikk`.

**Endra i §19:** dei to oversiktskorta («Last completed» og «Next check») går ut frå éin felles dato og må gjerast om.

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

Rapporten skal kunne brukast i Excel.

- [ ] Implementer XLSX-eksport dersom dette kan gjerast enkelt.
- [ ] Elles implementer CSV med tydeleg dokumentasjon om Excel-kompatibilitet.
- [ ] Eksporter alle nødvendige felt frå health check.
- [ ] Éin gjennomført health check skal kunne identifiserast som éi historisk kontroll.
- [ ] Ta med dato.
- [ ] Ta med nøkkelstatus.
- [ ] Ta med hardware-/firmware-resultat.
- [ ] Ta med seed/cloud-resultat.
- [ ] Ta med adresse-sti.
- [ ] Ta med programvareversjon og kompatibilitet.
- [ ] Ta med BIP327/SLIP39.
- [ ] Ta med KI-status.
- [ ] Ta med kontaktinfo-verifisering.
- [ ] Ta med neste sjekk.
- [ ] Ta med kommentarar.

---

# 11. Backend

Vel den enklaste teknologien som passar godt for ein liten lokal web-app.

- [x] Implementer SQLite.
- [x] Implementer database-initialisering/migrering — må utvidast med migreringa i §19.
- [x] Implementer lagring av nøklar.
- [x] Implementer lagring av health checks — éi innsending gjeld éin vald nøkkel (§19).
- [x] Implementer historikk.
- [x] Implementer varsellogikken — varseltekstane og vilkåra blir endra i §19.
- [ ] Implementer rapporteksport.
- [x] Implementer health endpoint.

Minimum:

- [x] `GET /health`
- [x] `GET /api/keys`
- [x] `GET /api/health-checks`
- [x] `GET /api/health-checks/:id`
- [x] `POST /api/health-checks` — kontrakten blir endra i §19.
- [ ] `GET /api/export`

**Merk:** `GET /api/alerts` er eit ekstra endepunkt som er lagt til utanom minimumslista, fordi dashboardet treng varsla. Det står ikkje i spesifikasjonen enno.

---

# 12. Frontend

- [x] Lag enkel responsiv web-UI.
- [x] Prioriter enkelheit framfor grafisk kompleksitet.
- [x] Bruk tydelege statusfelt.
- [x] Bruk faste val der status skal vere ein avgrensa verdi.
- [x] Vis problem tydeleg.
- [x] Vis kva som står att før ein health check kan lagrast.
- [ ] Sørg for at appen fungerer godt i vanleg StartOS-browser.

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
- [ ] Excel-kompatibel rapport kan eksporterast.
- [ ] Data overlever restart.
- [ ] Backup og restore fungerer.
- [ ] Ingen wallet-hemmeligheiter blir lagra.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- [x] 1. Opprett grunnleggande web-app.
- [x] 2. Opprett SQLite og datamodellen.
- [x] 3. Implementer dei tre faste nøklane.
- [x] 4. Implementer health check-skjemaet.
- [x] 5. Implementer lagring og historikk.
- [x] 6. Implementer varsellogikken.
- [ ] 7. Implementer dashboard.
- [ ] 8. Implementer rapporteksport.
- [ ] 9. Implementer StartOS package.
- [ ] 10. Implementer persistent storage og backup.
- [ ] 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** steg 4, 5 og 6 vart først fullførte før §19 vart vedteken. Dei vart sette tilbake til uticka og er no gjort på nytt i tråd med §19, med 60 grøne testar.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19. Ny avgjerd: registrering per nøkkel

Denne delen er den nyaste avgjerda og overstyrer motstridande krav ovanfor om at alle nøklane eller alle produkta må registrerast i same innsending. Eksisterande historiske data skal bevarast.

**Status:** implementert og verifisert (60 grøne testar).

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

## Lagring, historikk og verifikasjon

- [x] Knytt nøkkelsjekk, programvarekompatibilitet, BIP327/SLIP39 og relevante security status-resultat til same innsending og vald nøkkel.
- [x] Oppdater historikkdetaljen slik at han tydeleg viser vald nøkkel og tilhøyrande resultat.
- [x] Bevar eksisterande lagra registreringar; bruk trygg, bakoverkompatibel databasemigrering dersom datamodellen må endrast.
- [x] Oppdater servervalidering og testar: ei innsending skal krevje éin konfigurert nøkkel og gyldige, relevante resultat, og avvise manglande eller dupliserte nøkkel-/produktregistreringar og ugyldige programvareval.
- [x] Test registrering av kvar nøkkel, automatisk neste dato, relevante programvare- og security status-resultat, og at eldre historikk framleis kan lesast.
