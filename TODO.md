# TODO — Helsesjekk for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit **2-av-3 multisig-oppsett** med tre nøklar. Namn, type og adressesti blir konfigurerte ved første oppstart.

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

**Om dokumentet**

- §1–§18 er kravspecen og gjeld som han står.
- §19–§27 er korte samandrag av rundane. Alle reglane deira står i §1–§18; den fulle grunngjevinga ligg i git-historikken.
- Eit punkt utan avkryssingsboks er implementert og verifisert. `[ ]` markerer det som står att.
- **Status:** §1–§27 er implementerte og verifiserte, skjema versjon 11, testsuiten er grøn (337 testar). §18 steg 9–12 (StartOS) er **ikkje starta**.

## Språkkrav

- Brukargrensesnittet, app-tekst, kjeldekode, variabel- og funksjonsnamn, kommentarar og teknisk dokumentasjon skal vere på engelsk.
- `TODO.md` er på norsk; dette er det einaste unntaket.

---

# 1. Scope for første versjon

**Dette skal vere med**

- Ein enkel web-app med dashboard.
- Registrering av dei tre nøklane.
- Registrering av årleg health check, med kontroll av alle punkta i den årlege sjekklista.
- Varsel når eit kontrollpunkt krev oppfølging.
- Historikk over gjennomførte health checks.
- Automatisk forslag til neste sjekk, ca. eitt år fram i tid.
- Rapporteksport i CSV-format.
- Lokal SQLite-database.
- [ ] Persistent lagring på StartOS.
- [ ] StartOS health check.
- [ ] StartOS backup og restore.

**Dette skal ikkje vere med i første versjon**

Ingen AI-integrasjon, ingen Bitcoin-node-integrasjon, ingen Bitcoin-signering, ingen PSBT-generering eller signering, ingen seed phrase-lagring, ingen private key-lagring, ingen cloud sync av appdata, ingen ekstern database, ingen PWA/offline-database, ingen kalenderintegrasjon, ingen avansert analyse eller grafar, og inga støtte for fleire multisig-oppsett i MVP.

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- Appen skal aldri spørje etter seed phrase, private keys, PIN, passord eller wallet-hemmelegheiter, og aldri lagre slike.
- Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast; berre om kontaktinfo er stadfesta.
- Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- Appen skal vere lokal og enkel. Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast i MVP.

---

# 3. Nøkkeloppsettet appen er bygd for

Appen er bygd for eitt 2-av-3 multisig-oppsett med tre nøkkelplassar. Kvar nøkkel blir konfigurert éin gong ved første oppstart: namn, type (`hardware`/`cloud`) og adressesti.

- Namnet brukaren skriv, er produktetiketten overalt: skjema, varsel, historikk og CSV-eksport. Nøkkelnummeret blir vist saman med namnet der det trengst, t.d. `Key 1: ColdCard`.
- Nøkkeltypen styrer kontrollane, aldri nøkkelnummeret.
- `type` og `address_path` er identiteten til nøkkelen og er låste etter oppsettet. Namnet kan endrast i innstillingane.
- [ ] Ikkje bygg generell støtte for mange oppsett enno (fleire enn tre nøklar, eller andre tersklar enn 2-av-3).

Standardoppsettet appen vart bygd for, med døme-adressestiar:

| Nøkkel | Type | Eining | Adressesti (døme) |
|---|---|---|---|
| 1 | Hardware | SeedSigner | m/48'/0'/0'/2' |
| 2 | Hardware | Blockstream Jade | m/48'/1'/0'/2' |
| 3 | Cloud | Nunchuk | m/48'/2'/0'/2' |

---

# 4. Datamodell

SQLite, med så få tabellar som mogleg. Kvar tabell har éi rad per kolonne her; kolonnar merkte `*` er legacy-kolonnar som berre finst for gamle rader og aldri blir skrivne på nytt.

**`keys`** — dei tre nøkkelplassane.
`id`, `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `address_path`, `created_at`.

**`health_checks`** — éi rad per innsending, som gjeld éin vald nøkkel.
`id`, `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `sparrow_version*`, `nunchuk_version*`, `contact_info_verified`, `comments`.

**`key_checks`** — eitt record for den valde nøkkelen i kvar innsending.
`id`, `health_check_id`, `key_id`, `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`.

**`ai_security_checks`** — KI-sikkerheitsstatus per leverandør.
`id`, `health_check_id`, `provider`, `status`, `comments`.

**`wallet_software`** — lista brukaren vedlikeheld i innstillingane.
`id`, `name`, `created_at`.

**`alert_acknowledgements`** — kvitterte varsel.
`id`, `code`, `source`, `key_id` (§27), `check_id`, `reason`, `acknowledged_at`.

Reglar:

- `hardware_works`, `firmware_version` og `seed_backup_verified` gjeld berre hardware-nøklar.
- `seed_backup_verified` og `address_path_verified` har berre verdiane `OK` eller `PROBLEM`.
- `address_path` lagrar adressestien for den kontrollen.
- Når `available` er Nei, blir dei andre nøkkelfelta tømde, medan nøkkelnotatet blir behalde.
- Når `available` er Nei, blir `wallet_software` og `ai_security_checks` ikkje registrerte i det heile.
- `type` blir lagra éin gong ved første oppstart og er låst etterpå.
- `provider` lagrar det konfigurerte nøkkelnamnet og den valde programvara, ikkje faste produktnamn.
- `contact_info_verified` er fri tekst med to verdiar, og har ingen «not assessed»-verdi.
- `hardware_works` er obligatorisk for ein tilgjengeleg hardware-nøkkel.
- `name` kan endrast i innstillingane; `type` og `address_path` er identiteten til nøkkelen.
- `address_path_verified` blir sett av serveren ut frå ei samanlikning med `keys.address_path`, og blir ikkje sendt inn av brukaren.
- `wallet_software` i `health_checks` held fram som fri tekst, slik at eldre rader og fjerna listeelement held fram å visast rett.
- `address_path` må vere unik på tvers av dei tre nøklane: i oppsettet, i innstillingane og ved rotering.
- `reason` i `alert_acknowledgements` lagrar namnet på handlinga som lukka varselet, ikkje ein fri tekst.
- `tool_checks` finst ikkje. `device`, `seed_backup_status`, `address_verified`, `derivation_height`, `cloud_health_status` og `cloud_provider_operational` finst ikkje.

---

# 5. Statusverdiar

- Generelle kontrollar brukar `OK` eller `PROBLEM`. `NOT_ASSESSED` finst berre som den utleidde verdien for `software_compatibility_status` når nøkkelen ikkje kunne kontrollerast; ingen andre felt tilbyr eller godtar han.
- `seed_backup_verified` og `address_path_verified` brukar berre `OK` eller `PROBLEM`.
- KI-sikkerheitsstatus brukar nøyaktig `SECURE`, `PATCHED`, `VULNERABLE` og `COMPROMISED`.
- Kontaktstadfesting brukar `Confirmed current` eller `Needs external update`.
- `Hardware works` (`Yes`/`No`) og `Software compatibility` (`OK`/`PROBLEM`) krev eit aktivt val for ein tilgjengeleg nøkkel.
- `address_path_verified` er utleidd av serveren og er ikkje eit val i skjemaet.
- Same statuslogikk i database, validering, varsel, CSV-eksport og UI.
- Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.

---

# 6. Årleg health check — steg for steg

Stega følgjer seksjonane i skjemaet.

## Steg 1 — Schedule (01 / Schedule)

- Brukaren trykkjer `Start årleg health check`, og dagens dato blir føreslått automatisk.
- Neste sjekkdato blir rekna ut på serveren som eitt kalenderår etter sjekkdatoen, og kan ikkje redigerast i skjemaet.

## Steg 2 — Key (02 / Key)

- Brukaren vel kva nøkkel innsendinga gjeld. Ei innsending gjeld éin nøkkel.
- `Availability` er obligatorisk: Ja eller Nei.
- Ein nøkkel med eit ope varsel kan ikkje veljast, og skjemaet seier kva varsel som står i vegen.
- **Hardware-nøkkel:** `Hardware works` er obligatorisk (`Yes`/`No`), firmware-versjon blir registrert, og seed-backup intakt og stemmande med hardware gir `seed_backup_verified` (`OK`/`PROBLEM`). Kommentar ved behov.
- **Cloud-nøkkel:** berre `Availability` blir spurd om. Kommentar ved behov.
- **Adressesti (alle nøklar):** brukaren registrerer berre `Address path`, førehandsutfylt med nøkkelen sin lagra sti. Serveren samanliknar den innsende stien med `keys.address_path`: lik → `OK`, ulik → `PROBLEM`.
- Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd.
- Stemmer ikkje stien, viser nettlesaren eit påminningsvarsel før innsending, og kontrollen blir lagra som ein nøkkel som ikkje kunne kontrollerast.

## Steg 3 — Compatibility (03 / Compatibility)

- Brukaren vel éi wallet-programvare: `Sparrow Wallet`, eit namn frå innstillingane, eller namnet på ein konfigurert cloud-nøkkel. Ein cloud-nøkkel er låst til sitt eige namn.
- `Software version` blir registrert for alle nøklar, òg ein cloud-nøkkel.
- `OK` eller `PROBLEM`, med kommentar ved problem.
- For ein cloud-nøkkel er `Wallet software` og `Compatibility status` skjulte og utleidde.
- Når nøkkelen ikkje er tilgjengeleg, er feltet skjult og valfritt.

## Steg 4 — External research (04 / External research)

- Leverandørar per innsending: den valde nøkkelen (ved namn) og den valde programvara.
- Registrer status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) og ein kort kommentar.
- Berre den valde nøkkelen og den valde programvara blir registrerte. Appen kontaktar ikkje KI sjølv i MVP.
- Når nøkkelen ikkje er tilgjengeleg, blir ingen statusar registrerte.

## Steg 5 — Contact confirmation (05 / Contact confirmation)

- Stadfest at kontaktinformasjonen til nøkkelhaldaren til den valde nøkkelen er gyldig: `Confirmed current` eller `Needs external update`. Stadfestinga er obligatorisk, òg når nøkkelen ikkje er tilgjengeleg.
- Berre statusen blir lagra. Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 6 — Notes (06 / Notes)

- Eitt overordna kommentarfelt for observasjonar, og eigne kommentarar per nøkkel der det trengst.

## Oppsummering før lagring (Review-panelet)

- Før lagring viser appen alle kontrollpunkt, alle problem, alle manglande kontrollar, neste sjekkdato, handlingar som bør følgjast opp, og utleidde verdiar merkte som nettopp det.
- Brukaren må trykkje `Lagre health check` for å lagre kontrollen.
- Når adressestien ikkje stemmer, blir valet om å lagre likevel tydeleg merkt i oppsummeringa.

---

# 7. Varsel og oppfølging

Alle lagra kontrollar blir lesne, ikkje berre den nyaste. Like varsel (same `code` og `source`) blir slegne saman, og berre den nyaste blir vist. Kritiske varsel blir lista før informative, og nyaste kontroll først innanfor kvar alvor. Eit kvittert varsel held seg skjult til ein nyare kontroll for same `code` og `source` utløyser det igjen.

**Eit ope varsel som høyrer til ein nøkkel sperrar den nøkkelen** til varselet er lukka. Serveren handhevar regelen, så eit direkte API-kall ikkje kan omgå han. Sperringa gjeld berre den nøkkelen som har varselet.

| `code` | Alvor | Kjelde | Utløyst av | Slik blir det lukka |
|---|---|---|---|---|
| `key_unavailable` | critical | nøkkel | `available` = Nei | Rotering |
| `address_path_mismatch` | critical | nøkkel | Adressestien stemmer ikkje med den lagra | Rotering |
| `hardware_failure` | critical | nøkkel | `Hardware works` = No | Rotering, eller at hardware-walleten blir bytt med same seed |
| `seed_backup_problem` | critical | nøkkel | Seed-backup `PROBLEM` | Rotering |
| `software_incompatible` | critical | programvare | `software_compatibility_status` = `PROBLEM` | Fjerning av den feilande programvara i innstillingane, eller (§27) at hardware-walleten blir bytt når programvara er namnet på ein cloud-nøkkel |
| `security_vulnerable` | critical | nøkkel | KI-status `VULNERABLE` | Rotering, eller lukking utan tiltak |
| `security_vulnerable` | critical | programvare | KI-status `VULNERABLE` | Fjerning av programvara, eller lukking utan tiltak |
| `security_compromised` | critical | nøkkel | KI-status `COMPROMISED` | Rotering er påkravd |
| `security_compromised` | critical | programvare | KI-status `COMPROMISED` | Fjerning av programvara |
| `contact_info_unconfirmed` | info | kontaktinfo | Kontaktstadfesting `Needs external update` | Lukking, etter at kontaktinformasjonen er oppdatert eksternt |

- Kvar varselkode har eit fast sett av handlingar: `rotate`, `replace_hardware`, `remove_software`, `ignore`, `contact_updated`. Ei handling som ikkje høyrer til varselet, blir avvist.
- `rotate` blir utført i innstillingane, sidan han krev ein ny adressesti. Dei andre handlingane blir utførte der varselet står, kvar med sin eigen knappetekst og sitt eige stadfestingssteg.
- Kjelda til eit KI-varsel er leverandøren. Er han nøkkelen sitt eige konfigurerte namn, er nøkkelen kjelda og ei rotering lukkar varselet. Elles er leverandøren programvara nøkkelen køyrer med, og varselet blir lukka ved å fjerne ho frå innstillingane.
- Kvar handling krev ei stadfesting frå brukaren, og appen utfører aldri tiltaket sjølv. Han kontaktar heller aldri leverandørar eller KI-tenester.
- Eit varsel utan handling er ein feil i koden, ikkje ein tilstand brukaren kan hamne i.
- Eit varsel om nøkkel utilgjengeleg, adressestifeil eller seed-backup gjeld berre den nøkkelen, og resten av nøkkelfelta kan ikkje registrerast.

---

# 8. Dashboard

- Vis 2-av-3-oppsettet og status for kvar av dei tre nøklane, med siste sjekk og neste forfall per nøkkel.
- Oversiktskort «Next check» (tidlegaste forfall, med kva nøkkel det gjeld) og «Attention» (kor mange nøklar som har passert fristen). Om ein dato er passert, blir avgjort i nettlesaren.
- Vis alle aktive varsel, med kva registrering kvart varsel kjem frå, og handlinga som lukkar det.
- Knapp `Start årleg health check`, lenke `Historikk`, lenke `Download CSV` og lenke til innstillingane.
- Vis oppsettsteget i staden for dashboardet når nøkkeloppsettet manglar.
- Eit nøkkelkort viser ei tydeleg melding når nøkkelen har eit ope varsel, i staden for den vanlege statusen sin: kor mange varsel som står ope, at nøkkelen ikkje kan kontrollerast før dei er lukka, kva handling som lukkar det første, og ei lenkje til varsellista.

---

# 9. Historikk

- Vis alle gjennomførte health checks kronologisk, nyaste først, med kva nøkkel kvar innsending gjeld.
- Opne ein health check i read-only-visning med dato, neste sjekk, status per nøkkel, programvare og versjon, KI-status og kommentarar.
- Gamle health checks blir aldri overskrivne.
- Vis `Address path verified` som den utleidde verdien han er, og ikkje som eit brukarval.
- Vis namnet nøkkelen har no, sidan namnet kan endrast i innstillingane.
- (§27) Vis kva varsel som vart lukka på kontrollen, med kva handling og kva dato.

---

# 10. Rapporteksport

- `GET /api/export` gjev rein CSV (UTF-8, komma, CRLF, header). Ingen XLSX, og appen lovar ikkje Excel-kompatibilitet.
- Éi rad per nøkkelsjekk. Kolonnen `Check id` knyter saman rader frå same innsending.
- Inneheld dato, neste sjekk, nøkkelstatus, hardware/firmware, seed-resultat, adresse-sti, programvare og kompatibilitet, KI-status, kontaktstadfesting og kommentarar.
- Resultat med meir enn éin verdi per innsending ligg i éi celle som `SeedSigner: VULNERABLE; Sparrow Wallet: SECURE`.
- Statusverdiane blir skrivne slik dei er lagra. `0`/`1` blir skrivne som `No`/`Yes`.
- Nøkkelnamnet og nøkkeltypen kjem frå oppsettet, og namnet er namnet nøkkelen har no.
- (§27) Ny kolonne heilt til slutt med varsla som vart lukka på kontrollen, med handling og dato.

---

# 11. Backend

- SQLite med initialisering og migrering. Skjemaet er versjon 11.
- Lagring av nøklar, health checks, historikk og rapporteksport.
- Varsellogikken (§7).
- Health endpoint.
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.

Minimumsendepunkt: `GET /health`, `GET /api/keys`, `GET /api/health-checks`, `GET /api/health-checks/:id`, `POST /api/health-checks`, `GET /api/export`.

**Merk:** `GET /api/setup`, `POST /api/setup`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `POST /api/alerts/acknowledge`, `GET /api/key-status`, `GET /api/previous-values` og `GET /api/alerts` er ekstra endepunkt utanom minimumslista, fordi oppsettsteget, innstillingane, dashboardet og skjemaet treng dei. Dei står ikkje i spesifikasjonen enno.

- `POST /api/health-checks` krev éin konfigurert nøkkel, `available` og gyldige, relevante resultat, og avviser manglande eller dupliserte registreringar.
- `POST /api/health-checks` krev ikkje programvare eller KI-status når nøkkelen ikkje kunne kontrollerast, og avviser slike resultat med `400`.
- `POST /api/health-checks` avviser ein nøkkel som har eit ope varsel, med `409`, og regelen blir handheva før resten av valideringa.
- `POST /api/setup` lagrar nøkkeloppsettet éin gong med namn, type og adressesti, og avviser eit nytt oppsett med `409`.
- `POST /api/setup`, `POST /api/settings/keys` og `POST /api/keys/<id>/rotate` avviser ein adressesti som ein annan nøkkel alt har (`400` i oppsettet og roteringa, `409` i innstillingane).
- `GET /api/settings` gjev nøklane med adressestien deira og lista over wallet-programvare.
- `POST /api/settings/keys` lagrar eit nytt namn, og ein adressesti så lenge nøkkelen ikkje har nokon lagra kontroll.
- `POST /api/settings/wallet-software` lagrar heile lista, og lukkar varsla til ei programvare som blir fjerna.
- `POST /api/keys/<id>/rotate` roterer ein nøkkel med ein ny, unik adressesti, og kvitterer ut varsla hans.
- `POST /api/alerts/acknowledge` kvitterer ut eit varsel med `code`, `source` og handlinga som lukkar det.
- Feilkodar elles: ugyldig payload `400`, ukjend nøkkel eller varsel `404`, låst eller duplikat adressesti `409`, øydelagd database `500`.

---

# 12. Frontend

- Enkel responsiv web-UI. Enkelheit går framfor grafisk kompleksitet.
- Tydlege statusfelt, og faste val der statusen skal vere ein avgrensa verdi.
- Vis problem tydeleg, og vis kva som står att før ein health check kan lagrast.
- Skjul felt som ikkje gjeld for vald nøkkel eller vald programvare, og skjul programvare og KI-status når nøkkelen ikkje kunne kontrollerast. Eit skjult `required`-felt blokkerer innsendinga, så flagget må alltid clearast når feltet blir skjult.
- Eige oppsettsteg for namn, type og adressesti ved første oppstart.
- Skjemaet viser kva nøklar som er sperra av eit ope varsel, og kva handling som lukkar det.
- Eit påminningsvarsel før innsending når adressestien ikkje stemmer.
- Innstillingsside med `01 / Keys`, `02 / Wallet software` og `03 / Key rotation`, bygd for fleire tema seinare.
- Varselknappane har den teksten og det stadfestingssteget som høyrer til handlinga si, og varselet om programvare-inkompatibilitet peikar på innstillingane.
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

Unngå: Postgres, Redis, ekstern backend, ekstern cloud-service for appdata, og ekstra container utan konkret behov.

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 14. Lagring og backup

- [ ] SQLite-database skal liggje på persistent volum.
- [ ] Appdata skal overleve restart.
- [ ] Konfigurer StartOS backup av persistent data.
- [ ] Test backup og test restore.
- [ ] Verifiser at gamle health checks finst etter restore.

---

# 15. Sikkerheit og personvern

- Ingen seed phrase, private keys, wallet-passord eller sky-tokens i databasen.
- Ingen unødvendige personopplysningar. Kontaktinfo blir berre registrert som status (`Confirmed current` / `Needs external update`).
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.
- Ikkje implementer eigen kryptografi.
- Ikkje send data til eksterne tenester i MVP.
- Adressestien er ein offentleg derivasjonssti og inneheld inga hemmelegheit.

---

# 16. Testing

## Funksjonstest

- [ ] Opprett dei tre nøklane, start ein health check, fullfør alle kontrollpunkt, lagre han og vis han i historikken.
- [ ] Start ein ny health check, og verifiser at den gamle kontrollen framleis finst.

## Problemtest

- [ ] Test nøkkel utilgjengeleg, hardware-feil og seed-backup-feil.
- [ ] Test adressestifeil, både påminninga før innsending og varselet etterpå.
- [ ] Test programvare-inkompatibilitet, og at `Hardware works` og kontaktstadfestinga krev eit val.
- [ ] Test KI-status `VULNERABLE` og `COMPROMISED`, og kontaktinfo `Needs external update`.
- [ ] Test rotering av ein nøkkel, med og utan nytt namn, og at rotering krev ein ny adressesti.
- [ ] Test kvittering av eit varsel, og at eit nyare varsel kjem tilbake.
- [ ] Test at ein nøkkel med eit ope varsel ikkje kan få ein ny kontroll, og at nøkkelen blir ledig igjen når varselet er lukka.
- [ ] Test at to nøklar ikkje kan ha same adressesti, korkje i oppsettet, i innstillingane eller ved rotering.
- [ ] Test kvar varselhandling, og at eit varsel utan handlingar blir rekna som ein feil.
- [ ] Test at eit nøkkelkort viser ei varselmelding når nøkkelen har eit ope varsel.
- [ ] Test at fjerning av den feilande programvara lukkar `software_incompatible`.
- [ ] (§27) Test at eit lukka varsel viser seg i historikken og i CSV-en, med handling og dato.
- [ ] (§27) Test at eit kontaktvarsel gir `Needs action` og sperrar nøkkelen, og at nøkkelen blir ledig att ved `contact_updated`.
- [ ] (§27) Test at `software_incompatible` med ei cloud-nøkkel-programvare gir `replace_hardware` på den kontrollerte nøkkelen, og at det same varselet frå innstillingslista held fram med `remove_software`.

**Merk:** dette er dei manuelle nettlesartestane dine. Alt som er implementert, er òg dekt av testsuiten, men punkta står opne til du har køyrt dei i nettlesaren.

## StartOS-test

- [ ] Installer `.s9pk` på StartOS 0.4.0, start servicen og opne web UI.
- [ ] Utfør ein komplett test-check.
- [ ] Restart servicen, og verifiser at data framleis finst.
- [ ] Ta backup, restore backup, og verifiser data etter restore.

---

# 17. Ferdigkriterium for første release

Før første release skal alle desse vere oppfylte:

- [ ] Appen køyrer på StartOS 0.4.0.
- [ ] Dei tre nøklane er representerte i appen.
- [ ] Ein komplett årleg health check kan gjennomførast i nettlesaren, og alle årlege kontrollpunkt kan registrerast.
- [ ] KI-status kan registrerast som SECURE, PATCHED, VULNERABLE eller COMPROMISED.
- [ ] Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- [ ] Problem gir tydelege varsel, og eit varsel kan lukkast på den måten som høyrer til varselet.
- [ ] Neste sjekk blir lagra, og historikk fungerer.
- [ ] CSV-rapport kan eksporterast.
- [ ] Data overlever restart, og backup og restore fungerer.
- [ ] Ingen wallet-hemmelegheiter blir lagra.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- 1–8. Grunnleggande web-app, SQLite og datamodellen, dei tre nøklane, health check-skjemaet, lagring og historikk, varsellogikken, dashboardet og rapporteksport.
- [ ] 9. Implementer StartOS package.
- [ ] 10. Implementer persistent storage og backup.
- [ ] 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** §23–§27 kom inn etter steg 8 og er implementerte og verifiserte. Steg 9–12 er ikkje starta.

**Testar:** køyr `python3 -m unittest discover -s tests`. Suiten skal vere grøn både på Linux og på Windows-kopien.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19–22. Vedtekne avgjerder (implementerte og verifiserte)

- **§19 — registrering per nøkkel.** Ei innsending gjeld éin vald nøkkel, ikkje alle tre. Brukaren vel éi wallet-programvare med eitt versjonsfelt. Kvar nøkkel har sitt eige neste-sjekk-intervall.
- **§20 — skjulte felt som blir utleidde.** Eit felt som ikkje gjeld for den valde nøkkelen eller den valde programvara, blir skjult og utleidd. Førre lagra verdi blir fylt inn som ein vanleg input-verdi, og alt utleidd blir lista i Review-oppsummeringa, merkt som nettopp det.
- **§21 — engelske statusverdiar og alle varsel.** `IKKJE_VURDERT` → `NOT_ASSESSED`. Kvar råka tabell blir bygd opp att med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit. `GET /api/alerts` summerer alle lagra kontrollar, slår saman like varsel og listar kritiske først. «Helsesjekk» og `data/helsesjekk.sqlite3` er dokumenterte unntak frå engelskregelen.
- **§22 — ein nøkkel som ikkje kunne kontrollerast, registrerer ingenting elles.** Det gjeld både `available` = Nei og ein adressesti som ikkje stemmer: `wallet_software` blir `NULL`, `software_compatibility_status` blir `NOT_ASSESSED`, og eit innsend resultat er ein `400`, ikkje noko som blir kasta stille.

---

# 23. Konfigurerbart nøkkeloppsett (implementert og verifisert)

Kvar nøkkel blir konfigurert éin gong ved første oppstart: namn, type og adressesti. Namnet er produktetiketten overalt. `Wallet software`-vala er lista frå innstillingane (sådd med `Sparrow Wallet`) pluss namnet på kvar konfigurert cloud-nøkkel; eit hardware-nøkkelnamn er aldri eit software-val. Oppsettet ligg i SQLite saman med historikken, og ei ny database får eit oppsettsteg. Ei uleseleg database gir ein feil og blir ikkje behandla som ny. Nye endepunkt: `GET /api/setup` og `POST /api/setup`.

---

# 24. Obligatoriske val og ny skjemastruktur (implementert og verifisert)

`Hardware works` og kontaktstadfestinga er obligatoriske val med `Select status` som første, ugyldige alternativ. Kravet for `Hardware works` fell bort når nøkkelen ikkje kunne kontrollerast; kontaktstadfestinga blir spurd om uansett. Skjemaet har seks seksjonar: 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes. BIP327/SLIP39 er fjerna heilt, saman med `tool_checks`-tabellen og dataa hans.

---

# 25. Nøkkelidentitet, rotering, varselkvittering og innstillingar (implementert og verifisert)

Adressestien er identiteten til nøkkelen saman med typen, og er låst etter første lagra kontroll. Serveren utleier `address_path_verified` etter ei samanlikning som ignorerer blankteikn rundt verdien. Namnet er ein etikett som innstillingane kan endre, og historikk, varsel og CSV viser namnet nøkkelen har no. `POST /api/keys/<id>/rotate` stadfestar at nøkkelen er bytt ut, held eller endrar namnet, krev ein ny adressesti, kvitterer ut nøkkelens eigne varsel, og gjer inga endring i tidlegare kontrollar. Sida varslar om at rotering gir ei ny lommebok, slik at midla må flyttast frå den gamle multisig-oppsetninga før dei gamle nøklane blir kasserte. Innstillingane ligg på `/settings` med `01 / Keys`, `02 / Wallet software` og `03 / Key rotation`. Software-lista blir lagra heilt, er sådd med `Sparrow Wallet`, må aldri bli tom, og kan ikkje innehalde eit namn som alt kjem frå ein cloud-nøkkel. Skjemaversjon 10.

---

# 26. Sperring, unike adressestiar og varselhandlingar (implementert og verifisert)

Ein nøkkel med eit ope varsel kan ikkje få ein ny kontroll før varselet er lukka, og serveren handhevar regelen med `409`. Adressestien må vere unik på tvers av nøklane: `400` i oppsettet, `409` i innstillingane og `400` ved rotering, og meldinga nemner nøkkelen som har stien. Ei rotering krev ein ny, unik sti, og `address_path_unchanged` er fjerna. Kvar varselkode har sine eigne lukkehandlingar (§7), og den generiske kvitteringa er borte: `POST /api/alerts/acknowledge` tek handlinga og lagrar handlingsnamnet som `reason`. Eit nøkkelkort med eit ope varsel viser `Needs action`, kor mange varsel som står ope, og kva handling som lukkar det første.

---

# 27. Varselhandlingar i historikk og CSV, kontaktvarselet og cloud-programvare (implementert og verifisert)

Avtalt 05.10.2026. Skjemaet gjekk til versjon 11.

Bakgrunnen: ei lukking blir alt lagra i `alert_acknowledgements` (`code`, `source`, `check_id`, `reason` = handlingsnamnet, `acknowledged_at`), men ingenting les tabellen. Brukaren kan difor ikkje sjå kva som vart lukka, når og med kva handling. I tillegg finst to hol: kontaktvarselet høyrer ikkje til nokon nøkkel, og `software_incompatible` tilbyr `remove_software` òg når «programvara» er namnet på ein cloud-nøkkel, som aldri kan fjernast frå innstillingane.

- **Sperring.** Eit varsel som høyrer til ein nøkkel sperrar den nøkkelen til det er lukka. Det gjeld òg `contact_info_unconfirmed`, som har alvor `info`. `blocking_alert` og filteret i skjemaet matchar alt på `key_id`, så sperrekoden treng ikkje endrast.
- **Kontaktvarselet får ein nøkkel.** `key_id` = den kontrollerte nøkkelen, `source` = `Key N: <namn>` (same konvensjon som nøkkelvarsla), og meldinga namngjev nøkkelen: «The contact details for Key 1: SeedSigner need an external update. Update them in your external documentation, then close this alert.» Alvoret er framleis `info`, og handlinga framleis `contact_updated`.
- **`software_incompatible` får to former.** Når den registrerte `wallet_software` er namnet på ein konfigurert cloud-nøkkel: `key_id` = den kontrollerte nøkkelen, `source` = `Key N: <namn>`, og handlingane `[replace_hardware]`. Elles som i dag: `key_id` = `None`, `source` = programvanamnet, og handlingane `[remove_software]`.
- **Kvitteringa lagrar nøkkelen.** `alert_acknowledgements` får ei ny, nullable kolonne `key_id` (INTEGER, ingen FK, ingen CHECK).
- **Varselidentitet.** Eit varsel med `key_id` blir kvittert og skjult etter `(code, key_id)`; eit varsel utan `key_id` som før, etter `(code, source)`. Dette fiksar ein bug der `rotate` med `keep_name=false`, eller ei rein omdøyping i innstillingane, opnar eit lukka varsel att, fordi `source` inneheld namnet nøkkelen har no.
- **Lukkingar i historikk og CSV.** Lukkingar med `key_id` (altså `rotate`, `replace_hardware`, `contact_updated` og `ignore` med nøkkel som kjelde) skal visast i `GET /api/health-checks/<id>` og i CSV-eksporten. `remove_software` og `ignore` med programvare som kjelde skal ikkje visast. Lukkinga blir hengd på kontrollen ho lukka (`check_id`).

## Framtidig arbeid, ikkje no

- [ ] Fleire enn tre nøklar, og andre tersklar enn 2-av-3.
