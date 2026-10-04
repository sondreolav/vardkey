# TODO — Helsesjekk for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit **2-av-3 multisig-oppsett** med tre nøklar (namn, type og adressesti blir konfigurerte ved første oppstart, §23.2 og §25.1):

- Nøkkel 1: SeedSigner
- Nøkkel 2: Blockstream Jade
- Nøkkel 3: sky-nøkkel hos Nunchuk

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

Denne `TODO.md` er det einaste kravgrunnlaget du treng for MVP.

**Om dokumentet:** §1–§18 er kravspecen og gjeld som han står. §19–§22 er eit kort vedlegg med dei fire avgjerdene som vart tekne undervegs, alle innarbeidde i §1–§18. §23 (konfigurerbart nøkkeloppsett), §24 (obligatoriske val, fjerning av BIP327/SLIP39, ny skjemastruktur og skjemaversjon 9) og §25 (nøkkelidentitet, rotering, varselkvittering og innstillingar) er implementerte og verifiserte. §26 (sperring av ein nøkkel med ope varsel, unike adressestiar, rotering med ny adressesti og varselhandlingar) er **avtalt, men ikkje implementert**, og kjem etter §25. Den fulle grunngjevinga for kvar avgjerd ligg i git-historikken.

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

**Merk:** denne lista er eit varig forbod, ikke ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- [x] Appen skal aldri spørje etter seed phrase, private keys, PIN, passord eller wallet-hemmelegheiter.
- [x] Appen skal aldri lagre slike hemmelegheiter, og ikkje lagre kontaktinnhald.
- [x] Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast; berre om kontaktinfo er verifisert.
- [x] Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- [x] Appen skal vere lokal og enkel.
- [x] Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast i MVP.

---

# 3. Nøkkeloppsettet appen er bygd for

Appen er bygd for eitt 2-av-3 multisig-oppsett. Tabellen under viser standardoppsettet, med ein døme-adressesti:

| Nøkkel | Type | Einheit | Adressesti (døme) |
|---|---|---|---|
| 1 | Hardware | SeedSigner | m/48'/0'/0'/2' |
| 2 | Hardware | Blockstream Jade | m/48'/1'/0'/2' |
| 3 | Cloud | Nunchuk | m/48'/2'/0'/2' |

- [x] Vis 2-av-3 som oppsettet i dashboardet.
- [x] Ha tre nøkkelprofilar, éin for kvar nøkkel.
- [x] Ikkje bygg generell støtte for mange oppsett enno.
- [x] La brukaren gi nøklane namn, type og adressesti ved første oppstart (§23.2, §25.1).

**Merk:** §23.2 erstattar det faste oppsettet i denne seksjonen: kvar nøkkel blir konfigurert ved første oppstart, og namnet brukaren skriv, blir produktnamnet. §25.1 legg adressestien til, og §26.2 gjer han unik per nøkkel. Tabellen over viser standardoppsettet appen vart bygd for.

---

# 4. Datamodell

SQLite med så få tabellar som mogleg. Kvar tabell har éi rad per kolonne her; kolonnar merkte `*` er legacy-kolonnar som berre finst for gamle rader og aldri blir skrivne på nytt.

**`keys`** — dei tre nøkkelplassane.
`id`, `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `address_path` (§25.1), `created_at`.

**`health_checks`** — éi rad per innsending, som gjeld éin vald nøkkel (§19).
`id`, `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `sparrow_version*`, `nunchuk_version*`, `software_comments`, `contact_info_verified`, `comments`.

**`key_checks`** — eitt record for den valde nøkkelen i kvar innsending.
`id`, `health_check_id`, `key_id`, `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`.

**`ai_security_checks`** — KI-sikkerheitsstatus per leverandør.
`id`, `health_check_id`, `provider`, `status`, `comments`.

**`wallet_software`** — lista brukaren vedlikeheld i innstillingane (§25.4).
`id`, `name`, `created_at`.

**`alert_acknowledgements`** — kvitterte varsel (§25.3, §26.4).
`id`, `code`, `source`, `check_id`, `reason`, `acknowledged_at`.

Reglar:

- [x] `hardware_works`, `firmware_version` og `seed_backup_verified` er berre relevante for hardware-nøklar.
- [x] `seed_backup_verified` og `address_path_verified` har berre verdiane `OK` eller `PROBLEM`.
- [x] `address_path` lagrar adressestien for den kontrollen.
- [x] Når `available` er Nei, blir dei andre nøkkelfelta tømde, medan nøkkelnotatet blir behalde.
- [x] `seed_backup_status`, `address_verified` og `derivation_height` er fjerna (§19).
- [x] Når `available` er Nei, blir `wallet_software` og `ai_security_checks` ikkje registrerte i det heile (§22).
- [x] `type` i `keys` blir lagra éin gong ved første oppstart og er låst etterpå (§23.2).
- [x] `provider` lagrar det konfigurerte nøkkelnamnet og den valde programvara, ikkje faste produktnamn (§23.3).
- [x] `contact_info_verified` er fri tekst; dei faste listene er fjerna (§23.1, §23.3).
- [x] `device`-kolonnen er fjerna; det konfigurerte namnet er den einaste produktetikketten (§23.2).
- [x] `hardware_works` er obligatorisk (`0` eller `1`) for ein tilgjengeleg hardware-nøkkel (§24.1).
- [x] `contact_info_verified` er obligatorisk og har ingen «not assessed»-verdi (§24.1).
- [x] `tool_checks`-tabellen er fjerna (§24.2, §24.4).
- [x] `name` i `keys` kan endrast i innstillingane, medan `type` og `address_path` er identiteten til nøkkelen (§25.1, §25.2).
- [x] `cloud_health_status` og `cloud_provider_operational` er fjerna. Ein cloud-nøkkel registrerer berre `available` (§25.3, §25.6).
- [x] `address_path_verified` blir sett av serveren ut frå ei samanlikning med `keys.address_path`, og blir ikkje sendt inn av brukaren (§25.1).
- [x] `wallet_software` i `health_checks` held fram som fri tekst, slik at eldre rader og fjerna listeelement held fram å visast rett (§25.4).
- [ ] `address_path` må vere unik på tvers av dei tre nøklane, både i oppsettet, i innstillingane og ved rotering (§26.2).
- [ ] `reason` i `alert_acknowledgements` lagrar namnet på handlinga som lukka varselet, ikkje ein fri tekst (§26.4).

---

# 5. Statusverdiar

- [x] Generelle kontrollar brukar `OK` eller `PROBLEM`. `NOT_ASSESSED` finst berre som den utleidde verdien for `software_compatibility_status` når nøkkelen er utilgjengeleg, og ingen andre felt tilbyr eller godtar han (§24.1).
- [x] `seed_backup_verified` og `address_path_verified` brukar berre `OK` eller `PROBLEM`.
- [x] KI-sikkerheitsstatus brukar nøyaktig `SECURE`, `PATCHED`, `VULNERABLE` og `COMPROMISED`. Ingen andre.
- [x] Same statuslogikk i database, validering, varsel, CSV-eksport og UI.
- [x] Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.
- [x] Kontaktstadfesting brukar `Confirmed current` eller `Needs external update` i staden for Ja/Nei (§23.1).
- [x] `Software compatibility` krev eit aktivt val (`OK` / `PROBLEM`) for ein hardware-nøkkel (§23.1).
- [x] `Hardware works` krev eit aktivt val (`Yes` / `No`) for ein tilgjengeleg hardware-nøkkel (§24.1).
- [x] Kontaktstadfesting er obligatorisk og har ingen «not assessed»-verdi (§24.1).
- [x] BIP327- og SLIP39-statusane er fjerna saman med funksjonen sin (§24.2).
- [x] `NOT_ASSESSED` blir òg den utleidde verdien når adressestien ikkje stemmer (§25.1).
- [x] `address_path_verified` blir utleidd av serveren og er ikkje eit val i skjemaet (§25.1).

---

# 6. Årleg health check — steg for steg

Stega følgjer seksjonane i skjemaet.

## Steg 1 — Schedule (01 / Schedule)

- [x] Brukaren trykkjer `Start årleg health check`.
- [x] Dagens dato blir føreslått automatisk.
- [x] Neste sjekkdato blir rekna ut på serveren som eitt kalenderår etter sjekkdatoen, og kan ikkje redigerast i skjemaet.

## Steg 2 — Key (02 / Key)

- [x] Brukaren vel kva nøkkel innsendinga gjeld (§19). Ei innsending gjeld éin nøkkel.
- [x] `Availability` er obligatorisk: Ja eller Nei (§22).
- [ ] Ein nøkkel med eit ope varsel kan ikkje veljast, og skjemaet seier kva varsel som står i vegen (§26.1).

### Hardware-nøkkel

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] `Hardware works` er obligatorisk: Ja eller Nei (§24.1).
- [x] Registrer firmware-versjon.
- [x] Seed-backup intakt og stemmer med hardware → `seed_backup_verified` (`OK` / `PROBLEM`).
- [x] Kommentar ved behov.
- [x] Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd (§22).

### Cloud-nøkkel

- [x] Berre `Availability` blir spurt om.
- [x] Kommentar ved behov.

### Adressesti (alle nøklar)

- [x] Brukaren registrerer berre `Address path`, førehandsutfylt med nøkkelen sin lagra sti (§25.1).
- [x] `Address path verified` er ikkje lenger eit felt i skjemaet. Serveren samanliknar den innsende stien med `keys.address_path`: lik → `OK`, ulik → `PROBLEM` (§25.1).
- [x] Stemmer ikkje stien, viser nettlesaren eit påminningsvarsel før innsending, og kontrollen blir lagra som ein nøkkel som ikkje kunne kontrollerast (§25.1).

## Steg 3 — Compatibility (03 / Compatibility)

- [x] Brukaren vel éi wallet-programvare: `Sparrow Wallet` eller namnet på ein konfigurert cloud-nøkkel. Ein cloud-nøkkel er låst til sitt eige namn (§23.3).
- [x] Registrer versjonen til den valde programvara i `software_version`.
- [x] Registrer `OK` eller `PROBLEM`, med kommentar ved problem.
- [x] For ein cloud-nøkkel er `Wallet software` og `Compatibility status` skjulte og utleidde.
- [x] Når nøkkelen ikkje er tilgjengeleg, er feltet skjult og valfritt (§22).
- [x] Feltet heiter `Software version`, ikkje `Software version (if used)` (§25.5).
- [x] Ein cloud-nøkkel får òg `Software version`, medan `Wallet software` og `Compatibility status` held fram med å vere skjulte og utleidde (§25.5).

## Steg 4 — External research (04 / External research)

- [x] Leverandørar per innsending: den valde nøkkelen (ved namn) og den valde programvara (§23.3).
- [x] Registrer status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) og ein kort kommentar.
- [x] Berre den valde nøkkelen og den valde programvara blir registrerte; vidareføringa av ein tredje leverandør (§20) er fjerna (§23.3).
- [x] Når nøkkelen ikkje er tilgjengeleg, blir ingen statusar registrerte (§22).
- [x] Appen kontaktar ikkje KI sjølv i MVP.

## Steg 5 — Contact confirmation (05 / Contact confirmation)

- [x] Stadfest at kontaktinformasjonen til nøkkelhaldaren til den valde nøkkelen er gyldig, og lagre berre statusen (§23.1).
- [x] Stadfestinga er obligatorisk: `Confirmed current` eller `Needs external update` (§24.1). Ho blir spurt om også når nøkkelen er utilgjengeleg.
- [x] Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 6 — Notes (06 / Notes)

- [x] Eitt overordna kommentarfelt for observasjonar, og eigne kommentarar per nøkkel der det trengst.

## Oppsummering før lagring (Review-panelet)

- [x] Før lagring viser appen alle kontrollpunkt, alle problem, alle manglande kontrollar, neste sjekkdato, handlingar som bør følgjast opp, og utleidde verdiar merkte som nettopp det (§20).
- [x] Brukaren må trykkje `Lagre health check` for å lagre kontrollen.
- [x] Når adressestien ikkje stemmer, blir valet om å lagre likevel tydeleg merkt i oppsummeringa (§25.1).

---

# 7. Varsel og oppfølging

Alle lagra kontrollar blir lesne (§21). Kva som kan lukke eit varsel, står i §25.3 og §26.4.

- [x] Nøkkel ikkje tilgjengeleg → kritisk varsel om at nøkkelen må bytast ut før ein går vidare, og at resten av nøkkelfelta ikkje kan registrerast.
- [x] Hardware fungerer ikkje → seed-backupen bør testast på annan kompatibel hardware.
- [x] Seed-backup manglar eller er øydelagd → PROTOKOLL 3: Nøkkeltap skal aktiverast. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Programvare støttar ikkje lenger hardware → alternativ programvare eller løysing bør vurderast.
- [x] KI-status `VULNERABLE` → firmware- eller sikkerheitsproblemet må følgjast opp.
- [x] KI-status `COMPROMISED` → nøkkeltapsprosedyren må følgjast.
- [x] Kontaktinfo ikkje stadfesta → kontaktinformasjonen må oppdaterast i den eksterne dokumentasjonen.
- [x] Kritiske varsel blir lista før informative. Like varsel (same `code` og `source`) blir slegne saman, og berre den nyaste blir vist (§21).
- [x] Appen utfører aldri desse tiltaka sjølv.
- [x] Adressestien stemmer ikkje med nøkkelen → kritisk varsel om at nøkkelen må bytast ut, og at resten av nøkkelfelta ikkje kan registrerast (§25.1).
- [x] Varselet om cloud-helse er fjerna: det kunne ikkje utløysast frå skjemaet (§25.3).
- [x] Varselet om feila adresseverifisering er erstatta av varselet om adressestifeil (§25.3).
- [x] Eit kvittert varsel er skjult til ein nyare kontroll for same `code` og `source` utløyser det igjen (§25.3).
- [ ] Ein nøkkel med eit ope varsel kan ikkje få ein ny kontroll før varselet er lukka (§26.1).
- [ ] Kvar varselkode har ei fast sett av handlingar, kvar med sin eigen knappetekst og eige stadfestingssteg. Den generiske kvitteringa er fjerna (§26.4).
- [ ] `hardware_failure` har `rotate` og `replace_hardware`, og ingen generisk kvittering (§26.4).
- [ ] `software_incompatible` blir lukka ved at den feilande programvara blir fjerna frå innstillingane (§26.4, §26.7).
- [ ] `security_compromised` med nøkkel som kjelde kan berre lukkast med rotering (§26.4).

---

# 8. Dashboard

- [x] Vis 2-av-3-oppsettet og status for kvar av dei tre nøklane.
- [x] Vis siste sjekk og neste forfall per nøkkel — kvar nøkkel har sitt eige intervall (§19).
- [x] Oversiktskort «Next check» (tidlegaste forfall, med kva nøkkel det gjeld) og «Attention» (kor mange nøklar som har passert fristen). Om ein dato er passert blir avgjort i nettlesaren.
- [x] Vis alle aktive varsel, med kva registrering kvart varsel kjem frå (§21).
- [x] Knapp `Start årleg health check`, lenke `Historikk` og lenke `Download CSV`.
- [x] Vis oppsettsteget i staden for dashboardet når nøkkeloppsettet manglar (§23.2).
- [x] Vis handlinga som høyrer til kvart varsel, slik at brukaren kan lukke det (§25.3).
- [x] Lenke til innstillingane (§25.4).
- [ ] Eit nøkkelkort viser ei tydeleg melding når nøkkelen har eit ope varsel, i staden for den vanlege statusen sin, og seier kor mange varsel som står ope (§26.5).
- [ ] Nøkkelkortet peikar på handlinga som lukkar varselet, eller lenker til varsellista (§26.5).
- [ ] Varselet om programvare-inkompatibilitet lenker til innstillingane, der brukaren legg til ny programvare eller fjernar den feilande (§26.7).

---

# 9. Historikk

- [x] Vis alle gjennomførte health checks kronologisk, nyaste først, med kva nøkkel kvar innsending gjeld (§19).
- [x] Opne ein health check i read-only-visning med dato, neste sjekk, status per nøkkel, programvare og versjon, KI-status og kommentarar.
- [x] Gamle health checks blir aldri overskrivne.
- [x] Vis `Address path verified` som den utleidde verdien han er, og ikkje som eit brukarval (§25.1).
- [x] Vis namnet nøkkelen har no, sidan namnet kan endrast i innstillingane (§25.2).

---

# 10. Rapporteksport

- [x] `GET /api/export` gjev rein CSV (UTF-8, komma, CRLF, header). Ingen XLSX, og appen lovar ikkje Excel-kompatibilitet.
- [x] Éi rad per nøkkelsjekk. Kolonnen `Check id` knyter saman rader frå same innsending.
- [x] Inneheld dato, neste sjekk, nøkkelstatus, hardware/firmware, seed-resultat, adresse-sti, programvare og kompatibilitet, KI-status, kontaktstadfesting og kommentarar.
- [x] Resultat med meir enn éin verdi per innsending ligg i éi celle som `SeedSigner: VULNERABLE; Sparrow Wallet: SECURE`.
- [x] Statusverdiane blir skrivne slik dei er lagra (§21).
- [x] Nøkkelnamnet og nøkkeltypen kjem frå oppsettet (§23.3).
- [x] Kolonnen for cloud-leverandøren er fjerna saman med feltet (§25.6).
- [x] Nøkkelnamnet i eksporten er namnet nøkkelen har no (§25.2).

---

# 11. Backend

- [x] SQLite med initialisering og migrering. Skjemaet er no versjon 10 (§21, §23.1, §23.4, §24.4, §25.6).
- [x] Lagring av nøklar, health checks, historikk og rapporteksport.
- [x] Varsellogikken (§7).
- [x] Health endpoint.

Minimumsendepunkt:

- [x] `GET /health`
- [x] `GET /api/keys`
- [x] `GET /api/health-checks`
- [x] `GET /api/health-checks/:id`
- [x] `POST /api/health-checks`
- [x] `GET /api/export`

**Merk:** `GET /api/setup`, `POST /api/setup`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `POST /api/alerts/acknowledge`, `GET /api/key-status`, `GET /api/previous-values` og `GET /api/alerts` er ekstra endepunkt utanom minimumslista, fordi oppsettsteget, innstillingane, dashboardet og skjemaet treng dei. Dei står ikkje i spesifikasjonen enno.

- [x] `POST /api/health-checks` krev éin konfigurert nøkkel, `available` og gyldige, relevante resultat, og avviser manglande eller dupliserte registreringar (§22).
- [x] `POST /api/health-checks` krev ikkje programvare eller KI-status når nøkkelen er utilgjengeleg (§22).
- [x] `POST /api/setup` lagrar nøkkeloppsettet éin gong, krev unike og ikkje-tømme namn, og avviser eit nytt oppsett med `409` (§23.2).
- [x] `POST /api/setup` krev òg ein adressesti per nøkkel (§25.1).
- [x] `GET /api/settings` gjev nøklane med adressestien deira og lista over wallet-programvare (§25.4).
- [x] `POST /api/settings/keys` lagrar eit nytt namn, og ein adressesti så lenge nøkkelen ikkje har nokon lagra kontroll (§25.2).
- [x] `POST /api/settings/wallet-software` lagrar heile lista (§25.4).
- [x] `POST /api/keys/<id>/rotate` roterer ein nøkkel og kvitterer ut varsla hans (§25.2).
- [x] `POST /api/alerts/acknowledge` kvitterer ut eit varsel med `code`, `source` og ein årsak (§25.3).
- [x] `POST /api/health-checks` samanliknar adressestien og krev eit minimalt innhald når han ikkje stemmer, elles `400` (§25.1).
- [ ] `POST /api/health-checks` avviser ein nøkkel som har eit ope varsel, med `409` (§26.1).
- [ ] `POST /api/setup`, `POST /api/settings/keys` og `POST /api/keys/<id>/rotate` avviser ein adressesti som ein annan nøkkel alt har (§26.2).
- [ ] `POST /api/keys/<id>/rotate` tek ein ny `address_path` i staden for `address_path_unchanged`, og avviser den gamle stien og ein tom verdi (§26.3).
- [ ] `POST /api/alerts/acknowledge` tek handlinga (`rotate`, `replace_hardware`, `remove_software`, `ignore`, `contact_updated`) i staden for ein fri årsak, og avviser ei handling som ikkje høyrer til varselet (§26.4).
- [ ] Varselet oppgjev kva programvare som fekk resultatet, slik at fjerninga i innstillingane peikar på rett element (§26.7).

---

# 12. Frontend

- [x] Enkel responsiv web-UI. Enkelheit går framfor grafisk kompleksitet.
- [x] Tydlege statusfelt, og faste val der statusen skal vere ein avgrensa verdi.
- [x] Vis problem tydeleg.
- [x] Vis kva som står att før ein health check kan lagrast.
- [x] Skjul felt som ikkje gjeld for vald nøkkel eller vald programvare (§20, §21).
- [x] Skjul programvare og KI-status når nøkkelen er utilgjengeleg (§22).
- [x] Eige oppsettsteg for namn og type ved første oppstart (§23.2).
- [x] Bygg `Wallet software`-vala frå oppsettet i staden for ei fast liste (§23.3).
- [x] Følg den nye seksjonsrekkjefølgja: 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes (§24.3).
- [x] Oppsettsteget spør òg om adressesti (§25.1).
- [x] Ny innstillingsside med seksjonar for nøklar og wallet-programvare, bygd for fleire tema seinare (§25.4).
- [x] Eit påminningsvarsel før innsending når adressestien ikkje stemmer (§25.1).
- [x] `Wallet software`-vala kjem frå nøkkeloppsettet, cloud-nøklane og innstillingslista (§25.4).
- [ ] Skjemaet viser kva nøklar som er sperra av eit ope varsel, og kva handling som lukkar det (§26.1).
- [ ] Roteringsfeltet har eit eige tekstfelt for den nye adressestien, og namnefeltet er førehandsfylt med namnet nøkkelen har no (§26.3).
- [ ] Avstanden mellom `warning-note` og `rotation-list` i `03 / Key rotation` blir auka, utan at fargar eller innhald blir endra (§26.6).
- [ ] Varselknappane har den teksten og det stadfestingssteget som høyrer til handlinga si (§26.4).
- [ ] Varselet om programvare-inkompatibilitet lenker til innstillingane, og den feilande programvara kan fjernast derfrå (§26.7).
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

**Merk:** denne lista er eit varig forbod, ikke ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

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

- [x] Ingen seed phrase, private keys, wallet-passord eller sky-tokens i databasen.
- [x] Ingen unødvendige personopplysningar. Kontaktinfo blir berre registrert som status (`Confirmed current` / `Needs external update`).
- [x] Valider input på serveren.
- [x] Bruk parameteriserte SQL-spørringar.
- [x] Ikkje implementer eigen kryptografi.
- [x] Ikkje send data til eksterne tenester i MVP.
- [x] Adressestien er ein offentleg derivasjonssti og inneheld inga hemmelegheit.

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
- [ ] Test adressestifeil (mismatch), både påminninga før innsending og varselet etterpå (§25.1).
- [ ] Test programvare-inkompatibilitet.
- [ ] Test at `Hardware works` krev eit val.
- [ ] Test at kontaktstadfesting krev eit val.
- [ ] Test KI-status `VULNERABLE`.
- [ ] Test KI-status `COMPROMISED`.
- [ ] Test kontaktinfo `Needs external update`.
- [ ] Test rotering av ein nøkkel, med og utan nytt namn (§25.2).
- [ ] Test kvittering av eit varsel, og at eit nyare varsel kjem tilbake (§25.3).
- [ ] Test at ein nøkkel med eit ope varsel ikkje kan få ein ny kontroll, og at nøkkelen blir ledig igjen når varselet er lukka (§26.1).
- [ ] Test at to nøklar ikkje kan ha same adressesti, korkje i oppsettet, i innstillingane eller ved rotering (§26.2).
- [ ] Test at rotering krev ein ny adressesti, og at den gamle blir avvist (§26.3).
- [ ] Test kvar varselhandling, og at eit varsel utan handlingar blir rekna som ein feil (§26.4).
- [ ] Test at eit nøkkelkort viser ei varselmelding når nøkkelen har eit ope varsel (§26.5).
- [ ] Test at fjerning av den feilande programvara lukkar `software_incompatible` (§26.7).

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
- [ ] KI-status kan registrerast som SECURE, PATCHED, VULNERABLE eller COMPROMISED.
- [ ] Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- [ ] Problem gir tydelege varsel.
- [ ] Eit varsel kan lukkast på den måten som høyrer til varselet.
- [ ] Neste sjekk blir lagra.
- [ ] Historikk fungerer.
- [ ] CSV-rapport kan eksporterast.
- [ ] Data overlever restart.
- [ ] Backup og restore fungerer.
- [ ] Ingen wallet-hemmelegheiter blir lagra.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- [x] 1. Opprett grunnleggande web-app.
- [x] 2. Opprett SQLite og datamodellen.
- [x] 3. Implementer dei tre nøklane.
- [x] 4. Implementer health check-skjemaet.
- [x] 5. Implementer lagring og historikk.
- [x] 6. Implementer varsellogikken.
- [x] 7. Implementer dashboard.
- [x] 8. Implementer rapporteksport.
- [ ] 9. Implementer StartOS package.
- [ ] 10. Implementer persistent storage og backup.
- [ ] 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** steg 4, 5 og 6 vart først fullførte før §19 vart vedteken, og gjorde på nytt etterpå. Steg 4 og 6 vart kryssa av då §22 var verifisert.

**Merk:** §23, §24 og §25 er implementerte og verifiserte. §26 er avtalt, men ikkje implementert, og kjem før steg 9–12. Steg 9–12 er ikkje starta.

**Testar:** 283 grøne testar etter §25. Køyr `python3 -m unittest discover -s tests`.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19–22. Vedtekne avgjerder (implementerte og verifiserte)

Desse fire vart tekne undervegs og er no innarbeidde i §1–§18. Kvar referanse i §1–§18 peikar på avsnittet nedanfor. Den fulle grunngjevinga ligg i git-historikken. §23–§26 endra enkelte av detaljane etterpå; det står i så fall i parentes.

**§19 — registrering per nøkkel.** Ei innsending gjeld **éin vald nøkkel**, ikkje alle tre. Brukaren vel éi wallet-programvare med eitt versjonsfelt. `seed_backup_status`, `address_verified` og `derivation_height` er fjerna. Migreringa er bakoverkompatibel, og eldre historikk blir framleis vist. (§23.3 endra vala: `Sparrow Wallet` pluss namnet på kvar cloud-nøkkel, og ein cloud-nøkkel er låst til sitt eige namn.)

**§20 — skjulte felt som blir utleidde.** Ein cloud-nøkkel samlar berre `Availability`; cloud-helse, «leverandøren er i drift» og kompatibilitet blir utleidde. Førre lagra verdi blir fylt inn i feltet. Alt utleidd blir lista i Review-oppsummeringa, merkt som nettopp det. (§23.1 gjorde den førre verdien til ein vanleg input-verdi i staden for ein placeholder, §23.3 fjerna vidareføringa av ein tredje leverandør, og §25.3 fjerna dei to utleidde cloud-felta.)

**§21 — engelske statusverdiar, adressesti og alle varsel.** `IKKJE_VURDERT` → `NOT_ASSESSED`. Skjema versjon 6 (no versjon 10, §23.4, §24.4 og §25.6): kvar råka tabell blir bygd opp att med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit. `GET /api/alerts` summerer alle lagra kontrollar, med `check_id` og `checked_at`, slår saman like varsel og listar kritiske først. «Helsesjekk» og `data/helsesjekk.sqlite3` er dokumenterte unntak frå engelskregelen. (§25.1 erstatta kravet om at `Address path` berre blir lagra når verifiseringa er `OK`, og §25.3 la kvittering til. §26.1 gjer eit ope varsel til ei sperre for ein ny kontroll.)

**§22 — utilgjengeleg nøkkel gjer resten valfritt.** `Availability` er obligatorisk med berre Ja/Nei. Når han er Nei, blir programvare og KI-status skjulte og ikkje kravde, og dei må vere tomme i POST — elles svarar serveren `400`. Det blir ikkje lagra nokon slike rader, `wallet_software` er `NULL`, og `software_compatibility_status` blir `NOT_ASSESSED`. Ein cloud-nøkkel held fram med dei utleidde cloud-verdiane sine og gir det samanslåtte varselet. Databasen kravde inga endring. (§25.1 brukar same mønsteret for ein adressestifeil.)

---

# 23. Konfigurerbart nøkkeloppsett (implementert og verifisert)

Avtalt 02.10.2026, implementert og verifisert før steg 9–12 i §18. Reglane står i §3–§6; dette er berre eit kort samandrag, så fila er lett å lese.

- Kvar nøkkel blir konfigurert éin gong ved første oppstart: namn og type (`hardware`/`cloud`). (§25.1 legg adressestien til og §25.2 gjer namnet endreleg.)
- Namnet brukaren skriv er produktetiketten overalt: skjema, varsel, historikk og CSV-eksport. Nøkkelnummeret blir vist saman med namnet der det trengst, t.d. `Key 1: ColdCard`.
- Nøkkeltypen styrer kontrollane, aldri nøkkelnummeret. Ein cloud-nøkkel følgjer Nunchuk-modellen med det konfigurerte namnet.
- `Wallet software`-vala er `Sparrow Wallet` pluss namnet på kvar konfigurert cloud-nøkkel. Namn på hardware-nøklar er aldri eit software-val.
- Oppsettet blir lagra i SQLite saman med historikken. Nye databasar får eit oppsettsteg; eksisterande databasar blir migrerte frå nøkkelradene sine. Ei uleseleg database gir ein feil og blir ikkje behandla som ny.
- Skjemafiksar: `Firmware version`, `Address path` og `Software version` blir fylte med førre lagra verdi som ein vanleg input-verdi; `Software compatibility` krev eit aktivt val; kontaktspørsmålet gjeld berre nøkkelhaldaren til den valde nøkkelen, med verdiane `Confirmed current` / `Needs external update`.
- Skjemaversjon 8 då §23 vart ferdig (§24.4 tok han til 9, §25.6 til 10). Nye endepunkt: `GET /api/setup` og `POST /api/setup`.
- Verifisert med testsuiten. Nettlesarflytane og migreringa av ein verkeleg eldre database står att som manuelle testar i §16.

## Framtidig arbeid, ikke no

- [ ] Fleire enn tre nøklar, og andre tersklar enn 2-av-3.

---

# 24. Obligatoriske val, fjerning av BIP327/SLIP39 og ny skjemastruktur (implementert og verifisert)

Avtalt 03.10.2026, implementert og verifisert før steg 9–12 i §18. Der §24 seier noko anna enn §3–§12, gjeld §24. 24.2 og 24.4 vart gjorde i same runde, slik at skjemaversjonen gjekk til 9 med ein gong.

**§24.1 — obligatoriske val.** `Hardware works` og kontaktstadfestinga er obligatoriske val med `Select status` som første, ugyldige alternativ. Kravet for `Hardware works` fell bort når nøkkelen er utilgjengeleg; kontaktstadfestinga blir spurt om uansett. Serveren avviser manglande verdi med `400`. `NOT_ASSESSED` finst berre som den utleidde `software_compatibility_status` for ein utilgjengeleg nøkkel. Databasen kravde inga endring.

**§24.2 — BIP327/SLIP39 er fjerna.** Skjema, validering, varsel, historikk, CSV-kolonnar og `tool_checks`-tabellen med dataa sine er borte. Appen kan ikkje lenger registrere, vise eller eksportere slike resultat. Grunngjeving: appen skal haldast enkel og ryddig.

**§24.3 — skjemastruktur.** Rekkjefølgja er 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes. `04 / Standards` er borte, og seksjonane etter er omnummererte.

**§24.4 — datamodell og migrering.** Skjemaversjon 9. Migreringa droppar `tool_checks` med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit. `tool_checks` er ei barnetabell, så droppet krev inga omskriving av `health_checks`, og alle andre tabellar er uendra.

**§24.5 — testar og dokumentasjon.** Testane for BIP327/SLIP39 er fjerna, testar for dei obligatoriske vala (både i skjemaet og på serveren) og for migrering av ein database med `tool_checks` til versjon 9 er lagde til, og `README.md` er oppdatert.

---

# 25. Nøkkelidentitet, rotering, varselkvittering og innstillingar (implementert og verifisert)

Avtalt 04.10.2026, implementert og verifisert før steg 9–12 i §18. Reglane står i §3–§12; dette er berre eit kort samandrag, så fila er lett å lese. 283 grøne testar.

- **Adressestien er identiteten til nøkkelen, saman med typen.** `keys.address_path` blir lagra i oppsettet og er låst etter første lagra kontroll. Oppsettsteget spør om namn, type og adressesti, og skjemaet registrerer berre `Address path`, førehandsutfylt med nøkkelen sin lagra sti. (§26.2 gjer stien unik på tvers av nøklane.)
- **Serveren utleier `address_path_verified`.** Den innsende stien blir samanlikna med `keys.address_path` etter `strip`: lik → `OK`, ulik → `PROBLEM`. Eit innsend resultat blir ignorert. Ved ulik sti blir nøkkelen handsama som ein nøkkel som ikkje kunne kontrollerast (§22-mønsteret): berre stien, nøkkelnotatet, kontaktstadfestinga og den overordna kommentaren blir lagra, `wallet_software` blir `NULL`, `software_compatibility_status` blir `NOT_ASSESSED`, og eit kritisk varsel blir utløyst. Nettlesaren viser eit påminningsvarsel med ei avkryssing før innsending. Ein utilgjengeleg nøkkel registrerer ingen sti, og gir difor aldri eit slikt varsel.
- **Namnet er ein etikett som kan endrast i innstillingane**, medan typen og adressestien er låste. Historikk, varsel og CSV viser namnet nøkkelen har no.
- **Rotering** (`POST /api/keys/<id>/rotate`) stadfestar at nøkkelen er bytt ut, held eller endrar namnet, kvitterer ut nøkkelens eigne varsel, og gjer inga endring i tidlegare kontrollar. Sida varslar om at rotering gir ei ny lommebok, slik at midla må flyttast frå den gamle multisig-oppsetninga før dei gamle nøklane blir kasserte. (§26.3 erstattar stadfestinga av at adressestien er uendra med eit krav om ein ny, unik sti.)
- **Innstillingane** ligg på `/settings`, med `01 / Keys`, `02 / Wallet software` og `03 / Key rotation`, bygd for fleire seksjonar seinare. Software-lista blir lagra heilt, er sådd med `Sparrow Wallet`, må aldri bli tom, og kan ikkje innehalde eit namn som alt kjem frå ein cloud-nøkkel. Software-vala i skjemaet er lista pluss cloud-nøkkelnamna, og dashboardet lenkjer til innstillingane. (§26.6 rettar avstanden mellom varselnotatet og roteringslista, og §26.7 legg til fjerning av ei programvare som feilar.)
- **Skjemajusteringar:** feltet heiter `Software version`, gjeld òg ein cloud-nøkkel, og blir gjenbrukt frå førre lagra verdi for same nøkkel og programvare.
- **Skjema versjon 10:** `keys.address_path`, `wallet_software` og `alert_acknowledgements` er lagde til, og `cloud_health_status` og `cloud_provider_operational` er fjerna frå `key_checks`. Ingen datamigrering for eldre testdatabasar: `data`-mappa blir sletta og oppsettet gjort på nytt. Migreringa køyrer framleis med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit.

## 25.3 Varselkvittering

Eit kvittert varsel held seg skjult til ein nyare kontroll for same `code` og `source` utløyser det igjen. Kvitteringa blir lagra med `code`, `source`, `check_id` (den nyaste kontrollen som heva varselet), `acknowledged_at` og ein årsak. (§26.4 erstattar den generiske kvitteringa med faste handlingar per varselkode.)

| `code` | Alvor | Utløyst av | Slik blir det lukka |
|---|---|---|---|
| `key_unavailable` | critical | `available` = Nei | Rotering |
| `address_path_mismatch` | critical | `Address path` ulik nøkkelen sin lagra sti | Rotering |
| `hardware_failure` | critical | `Hardware works` = No | Rotering, eller berre lukking, sidan ein ny hardware-wallet med same seed er same nøkkel med same adressesti |
| `seed_backup_problem` | critical | Seed-backup `PROBLEM` | Rotering |
| `software_incompatible` | critical | `software_compatibility_status` = `PROBLEM` | Lukking, etter at alternativ programvare er lagd til i innstillingane |
| `security_vulnerable` | critical | KI-status `VULNERABLE` | Kjelde = nøkkel: rotering eller lukking. Kjelde = programvare: lukking |
| `security_compromised` | critical | KI-status `COMPROMISED` | Kjelde = nøkkel: rotering er påkravd. Kjelde = programvare: lukking |
| `contact_info_unconfirmed` | info | Kontaktstadfesting `Needs external update` | Lukking, med ei melding om at kontaktinformasjonen er oppdatert eksternt |

Kvart varsel oppgjev kva handlingar som lukkar det (`rotate`/`acknowledge`) og kva nøkkel det høyrer til, og kvar handling krev ei stadfesting frå brukaren. Appen utfører aldri eit tiltak sjølv. `cloud_provider_problem` og `address_verification_failed` er fjerna.

---

# 26. Sperring, unike adressestiar, rotering med ny sti og varselhandlingar (AVTALT, IKKJE IMPLEMENTERT)

Avtalt 04.10.2026, etter manuell testing i nettlesaren. Ingenting av dette er implementert, og punkta står opne til testane er grøne. Arbeidet kjem etter §25 og før steg 9–12 i §18. Fleire småting kan kome til etter kvart som brukaren testar vidare; dei blir lagde til her. Der §26 seier noko anna enn §25, gjeld §26.

Bakgrunnen for 26.1: samanslåinga i §21 held fram, så eit varsel frå ein gammal kontroll blir ikkje borte av at ein nyare kontroll for same nøkkel er frisk. Eit varsel blir difor lukka av brukaren, og eit ope varsel må ikkje kunne forsvinnast ved å registrere ein ny kontroll.

## 26.1 Sperring: ein nøkkel med ope varsel kan ikkje få ein ny kontroll

- [ ] Ein ny health check kan ikkje startast for ein nøkkel som har eit ope varsel. Skjemaet skal seie tydeleg kva varsel som står i vegen, kva handling som lukkar det, og kva nøklar som er ledige.
- [ ] Varselet må kunne lukkast, elles låser det nøkkelen: kvart varsel må ha minst éi lukkehandling (`actions` i §25.3 og §26.4). Eit varsel utan handling er ein feil, ikkje noko brukaren kan hamne i.
- [ ] Serveren handhevar regelen, ikkje berre skjemaet: `POST /api/health-checks` svarar `409` når den valde nøkkelen har eit ope varsel, slik at eit direkte API-kall ikkje kan omgå han.
- [ ] Skjemaet viser kva nøklar som er sperra, og lenker til varsla på dashboardet, slik at brukaren kan lukke dei først.
- [ ] Sperringa gjeld berre den nøkkelen som har varselet. Dei andre nøklane kan framleis få sin kontroll.
- [ ] Testar for sperringa: ein nøkkel med eit ope varsel gir `409` på serveren og ei tydeleg melding i skjemaet, medan ein nøkkel utan varsel fungerer som før. Testane skal òg dekkje at eit varsel alltid har minst éi lukkehandling.

## 26.2 Adressestien må vere unik

- [ ] Kvar nøkkel må ha sin eigen adressesti. To nøklar kan ikkje ha same sti, korkje i oppsettet, i innstillingane eller ved rotering.
- [ ] Oppsettsteget avviser ein sti som ein annan nøkkel alt har, med `400` og ei melding som nemner kva nøkkel som har han.
- [ ] Innstillingane avviser det same, med `409`.
- [ ] Rotering avviser det same, med `400` (§26.3).
- [ ] Samanlikninga skjer etter `strip` og utan omsyn til store og små bokstavar, slik at to stiar som berre skil seg i bokstavstorleik tel som like.
- [ ] Ei eldre testdatabase kan ha to nøklar med same sti, sidan §25 tillét det. Appen skal ikkje krasje: innstillingane viser kva nøklar som kolliderer, og ein ny kontroll for ein slik nøkkel blir avvist med ei melding om at stien må endrast først. Korleis dette skal handsamast må stadfestast med brukaren (§26.8).
- [ ] `README.md`, `TODO.md` og `ai-note.md` skal oppdaterast.

## 26.3 Rotering gir ein ny adressesti

- [ ] Målet med rotering er å byte ut nøkkelen med ein annan. Nøkkelen held same nøkkelnummer.
- [ ] Namnet kan haldast eller endrast. Tekstfeltet i innstillingane er førehandsfylt med namnet nøkkelen har no.
- [ ] Adressestien **må** bytast. Brukaren skriv inn ein ny sti, som må vere unik (§26.2). Den gamle stien blir avvist, og ein tom verdi blir avvist.
- [ ] `POST /api/keys/<id>/rotate` tek `replaced`, `keep_name`, `name` og den nye `address_path`. Stadfestinga `address_path_unchanged` er fjerna.
- [ ] Rotering oppdaterer nøkkelraden, lukkar varsla nøkkelen sjølv har heva, og gjer inga endring i tidlegare kontrollar.
- [ ] Sida held fram med å seie at rotering gir ei ny lommebok, slik at midla må flyttast frå den gamle multisig-oppsetninga før dei gamle nøklane blir kasserte.
- [ ] Sida seier òg kvifor stien må bytast: nøkkelen er ein annan, og stien er identiteten hans.

## 26.4 Kvar varselkode har sine eigne handlingar

- [ ] Den generiske kvitteringa blir erstatta av faste handlingar per varselkode. Kvar handling har sin eigen knappetekst og eit eige stadfestingssteg i nettlesaren.
- [ ] Handlingane er `rotate` (rotering i innstillingane), `replace_hardware` (ny hardware-wallet med same seed), `remove_software` (fjern den feilande programvara frå innstillingane), `ignore` (lukk eller ignorer varselet) og `contact_updated` (kontaktinformasjonen er oppdatert eksternt).
- [ ] `POST /api/alerts/acknowledge` tek handlinga i staden for ein fri årsak, og lagrar handlingsnamnet som årsak. Ei handling som ikkje høyrer til varselet blir avvist.
- [ ] Varsla får denne fordelinga:

| `code` | Kjelde | Handlingar |
|---|---|---|
| `key_unavailable` | nøkkel | `rotate` |
| `address_path_mismatch` | nøkkel | `rotate` |
| `hardware_failure` | nøkkel | `rotate`, `replace_hardware` |
| `seed_backup_problem` | nøkkel | `rotate` |
| `software_incompatible` | programvare | `remove_software` |
| `security_vulnerable` | nøkkel | `rotate`, `ignore` |
| `security_vulnerable` | programvare | `remove_software`, `ignore` |
| `security_compromised` | nøkkel | `rotate` |
| `security_compromised` | programvare | `remove_software`, `ignore` |
| `contact_info_unconfirmed` | kontaktinfo | `contact_updated` |

- [ ] `hardware_failure` mistar den generiske kvitteringa, fordi `replace_hardware` gjer den same jobben: brukaren stadfestar at hardware-walleten er bytt ut med ein ny, med same seed lasta inn. Nøkkelen og adressestien er uendra.
- [ ] Knappeteksten for `replace_hardware` blir til dømes `Replace hardware`, med stadfestinga «I have replaced the hardware wallet and restored the same seed on the new device.»
- [ ] `software_incompatible` mistar den generiske kvitteringa, fordi `remove_software` lukkar varselet (§26.7).
- [ ] `security_vulnerable` med nøkkel som kjelde kan roterast eller ignorerast, og ignoreringa krev eit stadfestingssteg.
- [ ] `security_compromised` med nøkkel som kjelde kan berre roterast, og har inga ignorering.
- [ ] `contact_info_unconfirmed` blir lukka med `contact_updated`, med stadfestinga «I have updated the contact details in my external documentation.»
- [ ] Eit varsel utan handlingar er ein feil i koden, og ein test skal dekkje det.

## 26.5 Nøkkelkortet viser eit ope varsel

- [ ] Eit nøkkelkort på dashboardet viser i dag den vanlege statusen sin, t.d. `Up to date`. Når nøkkelen har eit ope varsel, skal kortet i staden vise ei tydeleg melding om at nøkkelen krev handling, og kor mange varsel som står ope.
- [ ] Meldinga skal gjere det tydeleg at nøkkelen ikkje kan få ein ny kontroll før varselet er lukka (§26.1).
- [ ] Nøkkelkortet peikar på kva handling som lukkar varselet, eller lenker til varsellista.

## 26.6 Rotering: avstanden i innstillingane

- [ ] I `03 / Key rotation` ligg `div.warning-note` for nær `div.rotation-list`. Avstanden blir auka, slik at notatet og lista ikkje flyt saman.
- [ ] Endringa skal berre gjelde avstanden, ikkje fargar eller innhald.

## 26.7 Varselet om programvare-inkompatibilitet

- [ ] `software_incompatible` får ei melding som forklarer at den valde programvara ikkje lenger støttar hardwaren, og ei lenkje til innstillingane, der brukaren kan leggje til ei anna programvare.
- [ ] Programvara som fekk varselet blir fjerna frå lista når brukaren har lagd til ei ny. Å fjerne ho lukkar varselet.
- [ ] Er ho det einaste elementet i lista, må brukaren leggje til ei ny programvare først, sidan lista aldri kan bli tom (§25.4). Meldinga skal seie det.
- [ ] Er det andre element i lista, får brukaren ein knapp som fjernar den feilande programvara, og varselet blir borte med ho.
- [ ] Det same gjeld `security_vulnerable` og `security_compromised` når kjelda er programvara: same melding, same lenkje og same fjerning.
- [ ] Varselet må oppgje kva programvare som fekk resultatet, slik at lenkja og fjerninga peikar på rett element.
- [ ] Tilrådd mekanisme: varselet blir undertrykt medan den feilande programvara ikkje lenger står i lista, sidan det er tilstanden brukaren ser. Å lagre ei kvittering i staden er òg mogleg, men då må han haldast i samsvar med lista.
- [ ] Å fjerne eit listeelement rører ikkje lagra kontrollar, sidan `wallet_software` i `health_checks` er fri tekst.

## 26.8 Ope spørsmål, testar og dokumentasjon

- [ ] Stadfest med brukaren korleis ein eldre database med to like adressestiar skal handsamast (§26.2).
- [ ] Stadfest med brukaren om `ignore` òg skal gjelde for `security_compromised` med programvare som kjelde (§26.4).
- [ ] Stadfest med brukaren kva mekanisme som skal lukke `software_incompatible` når programvara blir fjerna (§26.7).
- [ ] Testar for alle punkta over, i tillegg til dei som alt står i §16.
- [ ] `README.md`, `TODO.md` og `ai-note.md` skal oppdaterast når dette er implementert.
