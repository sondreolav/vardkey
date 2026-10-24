# TODO — VardKey for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit **multisig-oppsett** (standard 2-av-3 med tre nøklar; terskel og talet på nøklar er valfritt). Namn, type, modell og adressesti blir konfigurerte ved første oppstart.

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

## Språkkrav

- Brukargrensesnittet, app-tekst, kjeldekode, variabel- og funksjonsnamn, kommentarar og teknisk dokumentasjon skal vere på engelsk.
- `TODO.md` er på norsk; dette er det einaste unntaket.

## Om dokumentet

- **§1–§18 er kravspecen og gjeld som han står.** Han skildrar appen slik han er no, ikkje slik han vart bygd.
- **§19–§31 er historikk.** Alle rundane der er ferdige og verifiserte, og står no som éi linje kvar. Reglane deira ligg i §1–§18 og i `ai-note.md`, som er handoveren.
- **§32 er runden som går no.** §32.1–§32.4 og §32.7 er utførte og verifiserte; dei står nedanfor som korte punktlister, slik at §-referansane i koden held, medan grunngjevinga ligg i git-historikken. Av §32.8 står berre **punkt 7** att, den manuelle gjennomgangen; deretter kjem §32.6 (dokumentasjonsdrifta) og §32.5 (hevinga av pakkeversjonen), i den rekkjefølgja. I §32.4 står berre BR-003 att, og han kan berre brukaren lukke.
- **Reglane under «Reglar som gjeld alle rundar» er bindande** for kvar framtidig endring.
- Eit punkt utan avkryssingsboks er implementert og verifisert. `[ ]` markerer det som står att.
- **Status:** alt til og med §31 er implementert og verifisert, og §32.1, §32.2, §32.3, §32.4 og §32.7 er utførte (sjå §32), med unnatak av BR-003, som berre brukaren kan lukke. I §32.8 er **steg A** (punkt 3, 4 og 2), **steg B** (punkt 1) og **steg C** (punkt 6 og 5) utførte, so skjemaet er no **versjon 13**; att står berre **punkt 7**, som berre brukaren kan gjere. Deretter kjem §32.6 og §32.5. StartOS-pakka er bygd, sideloda og køyrd på ein eigen StartOS 0.4.0-boks. Pakkeversjonen står på `0.1.0:0` og blir ikkje heva før §32 er ferdig og brukaren seier ifrå.

---

# 1. Scope for første versjon

**Dette skal vere med**

- Ein enkel web-app med dashboard.
- Registrering av nøklane i multisig-oppsettet.
- Registrering av årleg health check, med kontroll av alle punkta i den årlege sjekklista.
- Varsel når eit kontrollpunkt krev oppfølging.
- Historikk over gjennomførte health checks.
- Automatisk forslag til neste sjekk, ca. eitt år fram i tid.
- Rapporteksport i CSV-format.
- Lokal SQLite-database.
- Persistent lagring på StartOS.
- StartOS health check.
- StartOS backup og restore.
- Passordvern med ein adminbrukar, og ein veg til å nullstille appdata frå StartOS.

**Dette skal ikkje vere med**

Ingen AI-integrasjon, ingen Bitcoin-node-integrasjon, ingen Bitcoin-signering, ingen PSBT-generering eller signering, ingen seed phrase-lagring, ingen private key-lagring, ingen cloud sync av appdata, ingen ekstern database, ingen offline-database og ingen offline-registrering av kontrollar (ein installerbar PWA utan offline-data er tillaten), ingen kalenderintegrasjon, ingen avansert analyse eller grafar, og inga støtte for fleire multisig-oppsett — det er framleis berre **eitt** oppsett, men terskelen og talet på nøklar i det er valfrie.

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- Appen skal aldri spørje etter seed phrase, private keys, PIN, passord eller wallet-hemmelegheiter, og aldri lagre slike. Det gjeld *wallet*-hemmelegheiter: adminpassordet er den einaste akkrediteringa appen lagrar, og han blir lagra som ein `hashlib.scrypt`-hash, aldri i klartekst.
- Eit fritekstfelt avviser eit innlimt wallet-hemmelegheit lokalt, før noko blir lagra (sjå §15). Den korte åtvaringa mot å lime inn ei løyndom står **éin gong**, i nøkkeloppsettet, og blir ikkje gjenteken per fritekstfelt (sjå §12 og §15).
- Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast; berre om kontaktinfo er stadfesta.
- Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- Appen skal vere lokal og enkel. Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast.

---

# 3. Nøkkeloppsettet

Appen er bygd for **eitt** multisig-oppsett. Ved første oppstart gjev brukaren terskelen og talet på nøklar, og kvar nøkkel får namn, type (`hardware`/`cloud`), ein valfri modell/teneste og ein adressesti.

- Terskelen er `1 ≤ threshold ≤ key_count`, og `2 ≤ key_count ≤ 15`. Appen legg inga meining i tala sine.
- Namnet brukaren skriv, er produktetiketten overalt: skjema, varsel, historikk og CSV-eksport. Nøkkelnummeret blir vist saman med namnet der det trengst, t.d. `Key 1: ColdCard`.
- Nøkkeltypen styrer kontrollane, aldri nøkkelnummeret.
- `type` og `address_path` er identiteten til nøkkelen og er låste etter oppsettet. Namnet og modellen kan endrast i innstillingane. Berre ei rotering, som byter ut nøkkelen med ein ny, kan gi han den andre typen.

Standardoppsettet appen vart bygd for, med døme-adressestiar:

| Nøkkel | Type | Eining | Adressesti (døme) |
|---|---|---|---|
| 1 | Hardware | SeedSigner | m/48'/0'/0'/2' |
| 2 | Hardware | Blockstream Jade | m/48'/1'/0'/2' |
| 3 | Cloud | Nunchuk | m/48'/2'/0'/2' |

---

# 4. Datamodell

SQLite, med så få tabellar som mogleg. Kvar tabell har éi rad per kolonne her; kolonnar merkte `*` er legacy-kolonnar som berre finst for gamle rader og aldri blir skrivne på nytt.

**`keys`** — nøkkelplassane i det eine oppsettet, med éi aktiv rad per `key_number` og valfritt talet på pensjonerte rader attåt.
`id`, `key_number` (1–`multisig_key_count`), `name`, `type` (`hardware`/`cloud`), `model`, `address_path`, `active` (`0`/`1`), `rotated_at`, `created_at`.

**`health_checks`** — éi rad per innsending, som gjeld éin vald nøkkel.
`id`, `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `sparrow_version*`, `nunchuk_version*`, `contact_info_verified`, `comments`.

**`key_checks`** — eitt record for den valde nøkkelen i kvar innsending, med eit snapshot av nøkkelen slik han var då kontrollen vart lagra.
`id`, `health_check_id`, `key_id`, `key_name`, `key_type`, `key_model`, `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`.

**`ai_security_checks`** — KI-sikkerheitsstatus per leverandør, med den kontrollerte nøkkelen når leverandøren er nøkkelen sitt eige konfigurerte namn.
`id`, `health_check_id`, `provider`, `key_id`, `status`, `comments`.

**`wallet_software`** — lista brukaren vedlikeheld i innstillingane.
`id`, `name`, `created_at`.

**`alert_acknowledgements`** — kvitterte varsel.
`id`, `code`, `source`, `key_id`, `check_id`, `reason`, `acknowledged_at`.

**`app_settings`** — namn/verdi, for det som ikkje er historikk.
`name` (PRIMARY KEY), `value`. Held `multisig_threshold`, `multisig_key_count`, `admin_username`, `admin_password_hash`, `session_secret`, `failed_login_count` og `failed_login_until`.

Reglar:

- `hardware_works`, `firmware_version` og `seed_backup_verified` gjeld berre hardware-nøklar.
- `seed_backup_verified` og `address_path_verified` har berre verdiane `OK` eller `PROBLEM`.
- `address_path` lagrar adressestien for den kontrollen.
- Når `available` er Nei, blir dei andre nøkkelfelta tømde, medan nøkkelnotatet blir behalde.
- Når `available` er Nei, blir `wallet_software` og `ai_security_checks` ikkje registrerte i det heile.
- `type` blir lagra éin gong ved første oppstart og er låst etterpå; berre ei rotering kan gi nøkkelen den andre typen.
- `model` er valfri fri tekst (maks 60 teikn) og er rein dokumentasjon: ein hardware-modell eller, for ein cloud-nøkkel, namnet på tenesta. Han er ikkje ein del av identiteten, ikkje eit wallet-programvare-val, og blir ikkje brukt i varselkjelda.
- `provider` lagrar det konfigurerte nøkkelnamnet og den valde programvara, ikkje faste produktnamn.
- `contact_info_verified` er fri tekst med to verdiar, og har ingen «not assessed»-verdi.
- `hardware_works` er obligatorisk for ein tilgjengeleg hardware-nøkkel.
- `name` kan endrast i innstillingane; `type` og `address_path` er identiteten til nøkkelen.
- `address_path_verified` blir sett av serveren ut frå ei samanlikning med `keys.address_path`, og blir ikkje sendt inn av brukaren.
- `wallet_software` i `health_checks` held fram som fri tekst, slik at eldre rader og fjerna listeelement held fram å visast rett.
- `address_path` må vere unik på tvers av alle nøklane i oppsettet: i oppsettet, i innstillingane og ved rotering. Samanlikninga er kanonisk: `h`/`H` og `'` er same markør, og luft og store/små bokstavar blir ignorerte. Den lagra verdien blir aldri skriven om.
- `reason` i `alert_acknowledgements` lagrar namnet på handlinga som lukka varselet, ikkje ein fri tekst.
- `key_id` i `alert_acknowledgements` lagrar nøkkelen varselet høyrde til, eller `NULL` for eit programvarevarsel frå innstillingslista.
- Berre éi rad i `keys` per `key_number` er aktiv om gongen. Kravet blir handheva av eit **delvis unikt indeks** på `key_number` der `active = 1`, ikkje av ein `UNIQUE` på tabellen, so pensjonerte rader kan dele multisig-plassen (§32.8 punkt 5).
- `active` er `1` på den rada appen les som «nøkkelen», og `rotated_at` er tidsstempelet då rada vart pensjonert av ei rotering. Alle spørringar som les «nøkkelen» — oppsettet, innstillingane, skjemaet, dashboardet og roteringa — les den **aktive** rada, medan historikk, CSV og varsel les snapshottet på kontrollen.
- `key_name`, `key_type` og `key_model` i `key_checks` er eit **snapshot** av nøkkelen slik han var då kontrollen vart lagra. Korkje ei rotering eller ei omdøyping kan endre det, og migreringa backfyller snapshottet frå den kopla `keys`-rada (§32.8 punkt 5).
- `key_id` i `ai_security_checks` er den kontrollerte nøkkelen når `provider` er nøkkelen sitt eige konfigurerte namn, og `NULL` elles. Kjelda til eit KI-varsel blir difor avgjord av rada sjølv, og ho kan ikkje flippe når nøkkelen blir omdøypt eller rotert (§32.8 punkt 6).
- `failed_login_count` og `failed_login_until` i `app_settings` er innloggingsteljaren og sluttidspunktet for låsa (§32.8 punkt 2). Han overlever ein restart, og `failed_login_until` er eit sekundtal sidan epoch.
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
- Kontroll-datoen kan vere dagen i dag eller ein eldre dato, men ikkje ein dato i framtida: serveren avviser ein dato etter sin eigen dag med `400` og ei melding som seier det, og date-feltet i skjemaet har `max` sett til dagens lokale dato (§32.8 punkt 3). Ein kontroll som ikkje har skjedd enno, kan ikkje registrerast.
- Neste sjekkdato blir rekna ut på serveren som eitt kalenderår etter sjekkdatoen, og kan ikkje redigerast i skjemaet. Grensa endrar ikkje den utrekninga.

## Steg 2 — Key (02 / Key)

- Brukaren vel kva nøkkel innsendinga gjeld. Ei innsending gjeld éin nøkkel.
- `Availability` er obligatorisk: Ja eller Nei.
- Ein nøkkel med eit ope varsel kan ikkje veljast, og skjemaet seier kva varsel som står i vegen.
- **Hardware-nøkkel:** `Hardware works` er obligatorisk (`Yes`/`No`), firmware-versjon blir registrert, og seed-backup intakt og stemmande med hardware gir `seed_backup_verified` (`OK`/`PROBLEM`). Kommentar ved behov.
- **Cloud-nøkkel:** berre `Availability` blir spurd om. Kommentar ved behov.
- **Adressesti (alle nøklar):** brukaren registrerer berre `Address path`, førehandsutfylt med nøkkelen sin lagra sti. Serveren samanliknar den innsende stien med `keys.address_path` etter den kanoniske regelen i §4: lik → `OK`, ulik → `PROBLEM`.
- Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd.
- Stemmer ikkje stien, viser nettlesaren eit påminningsvarsel før innsending, og kontrollen blir lagra som ein nøkkel som ikkje kunne kontrollerast.

## Steg 3 — Compatibility (03 / Compatibility)

- Brukaren vel éi wallet-programvare: eit namn frå innstillingane, eller namnet på ein konfigurert cloud-nøkkel. Ein cloud-nøkkel er låst til sitt eige namn.
- `Software version` blir registrert for alle nøklar, òg ein cloud-nøkkel.
- `OK` eller `PROBLEM`, med kommentar ved problem.
- For ein cloud-nøkkel er `Wallet software` og `Compatibility status` skjulte og utleidde.
- Når nøkkelen ikkje er tilgjengeleg, er feltet skjult og valfritt.

## Steg 4 — External research (04 / External research)

- Leverandørar per innsending: den valde nøkkelen (ved namn) og den valde programvara.
- Registrer status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) og ein kort kommentar.
- Berre den valde nøkkelen og den valde programvara blir registrerte. Appen kontaktar ikkje KI sjølv.
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

Alle lagra kontrollar blir lesne, ikkje berre den nyaste. Like varsel (same `code` og `source`) blir slegne saman, og berre den nyaste blir vist. Kritiske varsel blir lista før informative, og nyaste kontroll først innanfor kvar alvor. Eit kvittert varsel held seg skjult til ein nyare kontroll for same `code` og `source` utløyser det igjen. Eit varsel som høyrer til ein nøkkel, blir i staden skjult etter nøkkelen, så ei omdøyping ikkje opnar det att.

**Eit ope varsel som høyrer til ein nøkkel sperrar den nøkkelen** til varselet er lukka. Serveren handhevar regelen, så eit direkte API-kall ikkje kan omgå han. Sperringa gjeld berre den nøkkelen som har varselet.

| `code` | Alvor | Kjelde | Utløyst av | Slik blir det lukka |
|---|---|---|---|---|
| `key_unavailable` | critical | nøkkel | `available` = Nei | Rotering |
| `address_path_mismatch` | critical | nøkkel | Adressestien stemmer ikkje med den lagra | Rotering |
| `hardware_failure` | critical | nøkkel | `Hardware works` = No | Rotering, eller at hardware-walleten blir bytt med same seed |
| `seed_backup_problem` | critical | nøkkel | Seed-backup `PROBLEM` | Rotering |
| `software_incompatible` | critical | nøkkel | `software_compatibility_status` = `PROBLEM`, og den registrerte programvara er namnet på ein konfigurert cloud-nøkkel | At hardware-walleten blir bytt |
| `software_incompatible` | critical | programvare | `software_compatibility_status` = `PROBLEM` | Fjerning av den feilande programvara i innstillingane |
| `security_vulnerable` | critical | nøkkel | KI-status `VULNERABLE` | Rotering, eller lukking utan tiltak |
| `security_vulnerable` | critical | programvare | KI-status `VULNERABLE` | Fjerning av programvara, eller lukking utan tiltak |
| `security_compromised` | critical | nøkkel | KI-status `COMPROMISED` | Rotering er påkravd |
| `security_compromised` | critical | programvare | KI-status `COMPROMISED` | Fjerning av programvara |
| `contact_info_unconfirmed` | info | nøkkel | Kontaktstadfesting `Needs external update` | Lukking, etter at kontaktinformasjonen er oppdatert eksternt |

**Forma på meldingane.** Kvar rad over har ein `message` i `alerts.py`, og alle elleve er skrivne om til same form (§32.3): kva som er gale, kva nøkkel eller programvare det gjeld, og kva som lukkar varselet. Meldingane er engelske, korte og konkrete, og dei seier ikkje at appen sjølv har gjort noko.

- **Meldinga gjentek ikkje namnet i kjelda.** `source` er anten `Key N: <namn>` eller namnet på programvara, og han blir vist rett over meldinga i varsellista, i parentes på nøkkelkortet og framføre meldinga i sperre-noten i skjemaet. Difor seier meldinga «this key» og ikkje nøkkelnamnet. Det einaste unntaket er nøkkelforma av `software_incompatible`: der er kjelda nøkkelen, medan meldinga namngjev programvara, sidan ho ikkje står nokon annan stad i den forma.
- **Dei to formene av ein KI-kode har kvar si melding.** `security_vulnerable` og `security_compromised` blir lukka av kvar si handling alt etter om kjelda er nøkkelen eller programvara, så kvar form seier kva som lukkar henne.
- **Handlinga står òg i knappen og i sperre-noten.** Det er medvite: knappen og noten seier kva brukaren kan trykkje på, medan meldinga skal stå åleine når ho blir lesen utan knappane.
- **Meldinga viser ikkje den interne koden.** `code` er for API-et og for `alert_acknowledgements`, ikkje for brukaren.

- Kvar varselkode har eit fast sett av handlingar: `rotate`, `replace_hardware`, `remove_software`, `ignore`, `contact_updated`. Ei handling som ikkje høyrer til varselet, blir avvist.
- `rotate` blir utført i innstillingane, sidan han krev ein ny adressesti. Dei andre handlingane blir utførte der varselet står, kvar med sin eigen knappetekst og sitt eige stadfestingssteg.
- Kjelda til eit KI-varsel blir avgjord av rada i `ai_security_checks`, ikkje av namna som er konfigurerte no. Ber rada den kontrollerte nøkkelen, er nøkkelen kjelda, ho blir skriven som `Key N: <namn>` på same måte som alle andre nøkkelvarsel, og ei rotering lukkar varselet. Elles er leverandøren programvara nøkkelen køyrer med, kjelda er berre namnet hennar, og varselet blir lukka ved å fjerne ho frå innstillingane. Ei omdøyping eller ei rotering kan difor ikkje gi eit nytt programvarevarsel ved sida av det nøkkelvarsla roteringa alt lukka (§32.8 punkt 6).
- Eit programvarevarsel frå innstillingslista har inga nøkkel og sperrar inga nøkkel. Eit programvarevarsel som kjem frå eit cloud-nøkkelnamn høyrer til den kontrollerte nøkkelen og sperrar han, sidan namnet aldri kan fjernast frå innstillingane.
- Lukka varsel blir viste i historia og i CSV-en, både dei som høyrer til ein nøkkel og dei som høyrer til ei programvare i innstillingslista: lukkinga heng på kontrollen ho lukka gjennom `check_id`, so eit lukka programvarevarsel står i same liste som ei rotering (§32.8 punkt 6).
- Kvar handling krev ei stadfesting frå brukaren, og appen utfører aldri tiltaket sjølv. Han kontaktar heller aldri leverandørar eller KI-tenester.
- Eit varsel utan handling er ein feil i koden, ikkje ein tilstand brukaren kan hamne i.
- Eit varsel om nøkkel utilgjengeleg, adressestifeil eller seed-backup gjeld berre den nøkkelen, og resten av nøkkelfelta kan ikkje registrerast.

---

# 8. Dashboard

- Vis multisig-oppsettet og status for kvar nøkkel, med neste forfall per nøkkel.
- Nøkkelkorta står rett under overskrifta på sida, utan ein eigen `Configured setup`-seksjon, utan `Your keys`-overskrift og utan nøkkelteljar (§32.7 punkt 2).
- Eitt oversiktskort, «Attention»: kor mange nøklar som har passert fristen, med kva nøklar det gjeld. Er ingen passert, står den tidlegaste sjekkdatoen der i staden, med kva nøkkel ho gjeld (`Earliest next check <dato>, for Key N: <namn>.`). Har ingen nøkkel ein dato, står fallbacken om å lagre ein health check. Om ein dato er passert, blir avgjort i nettlesaren.
- Vis alle aktive varsel, med kva registrering kvart varsel kjem frå, og handlinga som lukkar det. Ei tom varselliste viser ingen tekst; teljaren ved overskrifta seier `No alerts` (§32.7 punkt 4).
- Ingen navigasjonslenkjer i sjølve dashbordet: menyen i topplinja er vegen til skjemaet, innstillingane og historia, og eksporten ligg på history-sida (§32.7 punkta 1 og 5, og etterrunden punkta 1 og 4). Dashbordet har heller inga notelinje av eige; noten som forklarar eksporten står i eksportseksjonen på history-sida (etterrunden punkt 4).
- Vis oppsettsteget i staden for dashboardet når nøkkeloppsettet manglar.
- Eit nøkkelkort viser namn, adressesti, modell/teneste og type, og ei tydeleg melding når nøkkelen har eit ope varsel, i tillegg til datoane sine: kor mange varsel som står ope, at nøkkelen ikkje kan kontrollerast før dei er lukka, kva handling som lukkar det første, og ei lenkje til varsellista. Kortet viser nummeret og typen på den øvste linja (§32.2 punkt 6), modellen under namnet (punkt 8) og adressestien under han (punkt 7), og av datoane berre `Next check due` (punkt 9).

---

# 9. Historikk

- Vis alle gjennomførte health checks kronologisk, nyaste først, med kva nøkkel kvar innsending gjeld.
- Opne ein health check i read-only-visning med dato, neste sjekk, status per nøkkel, programvare og versjon, KI-status og kommentarar.
- Gamle health checks blir aldri overskrivne.
- Vis `Address path verified` som den utleidde verdien han er, og ikkje som eit brukarval.
- Vis namnet, typen og modellen nøkkelen vart lagra med på kontrollen, sidan snapshottet på kontrollen er frosen og korkje ei rotering eller ei omdøyping kan endre han (§32.8 punkt 5).
- Vis kva varsel som vart lukka på kontrollen, med kva handling og kva dato. Lukka programvarevarsel står i same liste som lukka nøkkelvarsel (§32.8 punkt 6).
- Kortet i lista viser datoen, nøkkelnummeret og namnet nøkkelen vart lagra med på kontrollen, og ein kort status: `All OK` eller `Needs follow-up` (§32.2 punkt 14 og §32.8 punkt 5). Det kjem frå `needs_follow_up` i oppsummeringa, som seier om kontrollen reiste noko å følgje opp.
- Programvara og versjonen hennar står på éi line, t.d. `Sparrow Wallet 2.5.1`, og modellen og firmware-versjonen står på éi line, t.d. `Blockstream Jade 1.4.1` (runden 32.1). Manglar ein del, står resten åleine; manglar båe, står `—`.
- Lukke-tabellen på ein kontroll viser `Alert`, `Action` og `Closed`. Kjelda er inga eiga kolonne (runden 32.1).
- Sida har ein eigen `Export`-seksjon etter lista, før detaljseksjonen, med tittellinja `Download the report`, lenkja `Download CSV` utan `download`-attributt — så filnamnet frå `Content-Disposition` vinn — og noten som forklarar eksporten rett under lenkja (§32.7 punkt 5 og etterrunden punkta 1 og 4). Det er den einaste staden eksporten blir lasta ned frå, og sida startar ikkje ein ny kontroll.
- `View` i lista opnar kontrollen på ankeret `#history-detail`, og det same gjer ei innsending frå skjemaet, så brukaren landar på kontrollen og ikkje på toppen av sida (§32.7 etterrunden punkt 3).

---

# 10. Rapporteksport

- `GET /api/export` gjev rein CSV (UTF-8, komma, CRLF, header). Ingen XLSX, og appen lovar ikkje Excel-kompatibilitet.
- Éi rad per nøkkelsjekk. Kolonnen `Check id` knyter saman rader frå same innsending.
- Inneheld dato, neste sjekk, nøkkelstatus, hardware/firmware, seed-resultat, adresse-sti, programvare og kompatibilitet, KI-status, kontaktstadfesting og kommentarar.
- Resultat med meir enn éin verdi per innsending ligg i éi celle som `SeedSigner: VULNERABLE; Sparrow Wallet: SECURE`.
- Statusverdiane blir skrivne slik dei er lagra. `0`/`1` blir skrivne som `No`/`Yes`.
- Ei tekstcelle som eit rekneark ville lese som ein formel — `=`, `+`, `-`, `@` eller eit kontrollteikn, òg etter leiande mellomrom — får ein leiande apostrof, slik at ho blir tekst. Kolonnenamna, kolonnerekkjefølgja og alle vanlege verdiar er uendra.
- Nøkkelnamnet og nøkkeltypen kjem frå snapshottet på kontrollen, so ei rotering eller ei omdøyping kan ikkje skrive om ei eldre rad (§32.8 punkt 5).
- Nedlastinga heiter `YYYY-MM-DD-vardkey-export.csv`, med datoen serveren har når han svarar.
- Siste kolonne, `Follow-up closed`, listar alle varsla som vart lukka på kontrollen, som `code: action (YYYY-MM-DD)`, anten dei høyrer til ein nøkkel eller til ei programvare i innstillingslista (§32.8 punkt 6).

---

# 11. Backend

- SQLite med initialisering og migrering. Skjemaet er versjon 13.
- Lagring av nøklar, health checks, historikk og rapporteksport.
- Varsellogikken (§7).
- Health endpoint, som er det einaste endepunktet utanfor innlogginga.
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.

Minimumsendepunkt: `GET /health`, `GET /api/keys`, `GET /api/health-checks`, `GET /api/health-checks/:id`, `POST /api/health-checks`, `GET /api/export`.

**Merk:** `GET /api/session`, `POST /api/admin`, `POST /api/login`, `POST /api/logout`, `GET /api/setup`, `POST /api/setup`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `POST /api/alerts/acknowledge`, `GET /api/key-status`, `GET /api/previous-values` og `GET /api/alerts` er ekstra endepunkt utanom minimumslista, fordi oppsettsteget, innstillingane, dashboardet, skjemaet og innlogginga treng dei. Dei står ikkje i spesifikasjonen enno.

- `POST /api/health-checks` krev éin konfigurert nøkkel, `available` og gyldige, relevante resultat, og avviser manglande eller dupliserte registreringar.
- `POST /api/health-checks` krev ikkje programvare eller KI-status når nøkkelen ikkje kunne kontrollerast, og avviser slike resultat med `400`.
- `POST /api/health-checks` avviser ein nøkkel som har eit ope varsel, med `409`, og regelen blir handheva før resten av valideringa.
- `POST /api/setup` lagrar multisig-tala og nøkkeloppsettet éin gong med namn, type, modell og adressesti, og avviser eit nytt oppsett med `409`.
- `POST /api/setup`, `POST /api/settings/keys` og `POST /api/keys/<id>/rotate` avviser ein adressesti som ein annan nøkkel alt har (`400` i oppsettet og roteringa, `409` i innstillingane). Samanlikninga er kanonisk, sjå §4.
- `GET /api/settings` gjev nøklane med adressestien og modellen deira og lista over wallet-programvare.
- `POST /api/settings/keys` lagrar eit nytt namn og ein modell, og ein adressesti så lenge nøkkelen ikkje har nokon lagra kontroll. Typen er aldri med i payloaden. Han skriv den aktive rada på plass, so han er ei omdøyping og ikkje ei rotering.
- `POST /api/settings/wallet-software` lagrar heile lista, og lukkar varsla til ei programvare som blir fjerna.
- `POST /api/keys/<id>/rotate` roterer ein nøkkel med ein ny, unik adressesti, kan gi nøkkelen den andre typen, og kvitterer ut varsla hans. Roteringa legg til **ei ny rad** i `keys` med same `key_number`, merkjer den gamle rada som inaktiv og set `rotated_at` på henne, medan kvitteringane blir skrivne på den gamle rada, som er den rada varsla høyrer til (§32.8 punkt 5).
- `POST /api/keys/<id>/rotate` avviser med `409` ein typeendring som ville gjort nøkkelen til ein cloud-nøkkel under eit namn som wallet-programvare-lista alt har.
- `POST /api/alerts/acknowledge` kvitterer ut eit varsel med `code`, `source` og handlinga som lukkar det.
- `POST /api/login` avgrensar feila forsøk: etter fem mislukka forsøk på rad blir vidare innloggingar avviste i 15 minutt med `429` og ei melding som seier kor lenge det står att. Eit rett passord i låseperioden blir òg avvist, så svaret røpar ikkje om passordet var rett, og eit vellukka innlogging nullstiller teljaren. Teljaren ligg i `app_settings`, så han overlever ein restart. `POST /api/admin`, den lokale bootstrapen, blir ikkje avgrensa (§32.8 punkt 2).
- `GET /api/health-checks/<id>` gjev òg `closed_alerts`, alle lukkingane som høyrer til kontrollen — både dei som høyrer til ein nøkkel og dei som høyrer til ei programvare i innstillingslista (§32.8 punkt 6) — og kvart nøkkelrecord ber `model` i tillegg til felta det alt hadde, så historia kan vise modellen saman med firmware-versjonen (runden 32.1). Felta kjem i tillegg, og dei eksisterande namna er uendra.
- `GET /api/health-checks` gjev kvar oppsummering med dei same felta som før, og i tillegg `key_names` (namnet kvar nøkkel vart lagra med på kontrollen, lese frå snapshottet, i same rekkjefølgje som `key_numbers`) og `needs_follow_up` (om kontrollen reiste noko å følgje opp, rekna ut av varselreglane i §7, og ein eigenskap ved den lagra kontrollen — han endrar seg ikkje når brukaren lukkar varselet seinare). Felta kjem i tillegg, sjå §32.2 punkt 14 og §32.8 punkt 5.
- Feilkodar: ugyldig payload `400`, ukjend nøkkel eller varsel `404`, låst eller duplikat adressesti `409`, øydelagd database `500`, manglande eller ugyldig sesjon `401`, manglande eller ugyldig CSRF-token `403`, og for mange feila innloggingsforsøk på rad `429` (§32.8 punkt 2). Eit fritekstfelt som ser ut som ei wallet-løyndom er òg ein `400` (sjå §15).
- `_send_security_headers()` legg `X-Robots-Tag: noindex, nofollow` på kvart svar — sider, JSON, redirect, CSV og statiske filer — så indekseringssperra står i éin stad (§32.7 punkt 6).

---

# 12. Frontend

- Enkel responsiv web-UI. Enkelheit går framfor grafisk kompleksitet.
- Tydlege statusfelt, og faste val der statusen skal vere ein avgrensa verdi.
- Vis problem tydeleg, og vis kva som står att før ein health check kan lagrast.
- Skjul felt som ikkje gjeld for vald nøkkel eller vald programvare, og skjul programvare og KI-status nøkkelen ikkje kunne kontrollerast. Eit skjult `required`-felt blokkerer innsendinga, så flagget må alltid clearast når feltet blir skjult.
- Eige oppsettsteg ved første oppstart: terskel, talet på nøklar, og namn, type, modell og adressesti per nøkkel.
- Eit innloggingssteg framfor alt anna, og eit opprett-admin-steg når ingen admin finst enno.
- Topplinja har ein `Menu`-knapp med nedtrekk på alle fem app-sidene, i denne rekkjefølgja: `Dashboard` → `/`, `Start health check` → `/health-check`, `Settings` → `/settings`, `History` → `/history`, ei skiljelinje, og `Sign out` som gjer det same som før. Panelet er skjult til det blir opna, og det blir lukka på `Escape`, ved klikk utanfor og etter eit val. Sida brukaren alt står på er gråa ut, er ikkje ei lenkje og kan ikkje klikkast, og ho ber `aria-current="page"`. `session.js` byggjer både knappen, panelet og `.topbar-actions`-innpakninga, så markupen på sidene er uendra. `/login` har ingen meny, sidan `session.js` ikkje blir lasta der (§32.7 punkt 1 og etterrunden punkt 2).
- Topplinja er fest til toppen: `.topbar` er `position: sticky; top: 0` med ein `z-index` som held ho over sideinnhaldet og under meny-panelet, so ho blir verande synleg når ein scrollar. Ho er eit flex-barn av `body`, som ikkje set nokon `overflow`, og det er difor festet verkar. Utan inline stil, og utan `border-radius`, `box-shadow` eller gradient (§32.8 punkt 4).
- Skjemaet viser kva nøklar som er sperra av eit ope varsel, og kva handling som lukkar det.
- Eit påminningsvarsel før innsending når adressestien ikkje stemmer.
- Date-feltet for kontroll-datoen har `max` sett til dagens lokale dato, so datoveljaren ikkje tilbyr ein dato serveren ville avvise (§32.8 punkt 3).
- Innstillingsside med `01 / Wallet software` og `02 / Key rotation`, bygd for fleire tema seinare. Nøkkelnamnet, modellen, adressestien til ein nøkkel utan lagra kontroll, og roteringa med ny type blir alle endra i roteringsseksjonen, og éin knapp lagrar alt. Det finst ikkje lenger ein eigen `01 / Keys`-seksjon.
- Varselknappane har den teksten og det stadfestingssteget som høyrer til handlinga si, og varselet om programvare-inkompatibilitet peikar på innstillingane.
- Den korte åtvaringa mot å lime inn ei løyndom står **éin gong**, i nøkkeloppsettet, i tillegg til sidenotisen, med stilen `.secret-warning` (§15). Ho blir ikkje gjenteken per fritekstfelt.
- Appen skal kunne installerast som ein PWA utan offline-data.
- Sørg for at appen fungerer godt i vanleg StartOS-browser.
- Ingen indeksering og ingen bots: alle seks sidene ber `<meta name="robots" content="noindex, nofollow">`, `X-Robots-Tag: noindex, nofollow` står på kvart svar, og `static/robots.txt` svarar `Disallow: /` (§32.7 punkt 6).

---

# 13. StartOS 0.4.0

Appen er éin enkel StartOS-service.

```text
StartOS 0.4.0
└── VardKey
    ├── Web UI
    ├── Backend/API
    ├── SQLite
    └── Persistent data
```

- Opprett StartOS package.
- Opprett manifest.
- Opprett service-definisjon.
- Opprett HTTP web-interface.
- Opprett persistent volume.
- Opprett health check.
- Opprett backup-oppsett.
- Opprett installasjons-/brukarinstruksjonar.
- Bygg `.s9pk`.
- Verifiser at pakken kan installerast på StartOS 0.4.0.

**Merk:** alle ti punkta er oppfylte. Pakka ligg i repoet, er bygd til `vardkey_x86_64.s9pk`, sideloda og køyrd på ein eigen StartOS 0.4.0-boks. To handlingar ligg i `Actions & Config`: `Delete all data` og `Set Admin Password`.

Frå §32.8 punkt 1 har pakka i tillegg ei **påkravd oppgåve** (task) som skal halde servicen tilbake til adminpassordet er sett. Ho blir reist og lukka av eit init-skript, `startos/init/requireAdmin.ts`, som er registrert i `sdk.setupInit()` etter handlingane: medan databasen ikkje har nokon admin, held han oppgåva `Set Admin Password` oppe med `severity: 'important'`, og når ein admin finst, lukkar han henne att. Oppgåva peikar på den **eksisterande** handlinga, som køyrer `maintenance.py set-admin-password` i ein `withTemp`-subcontainer, so passordet blir framleis generert **inne i containeren** og skrive ut éin gong — ingenting går frå verten inn i containeren, som argument eller på stdin. Init-skriptet kan ikkje lese databasen frå sitt eige JavaScript, so det spør eit lite `python3`-probe i ein `withTemp`-subcontainer som les `app_settings` **readonly**. Proben **feilar ope**: kan han ikkje køyrast, blir inga oppgåve reist, so ein brukar som alt har ein admin aldri blir sperra av eit gjet. Readiness-sjekken mot `/health` og `/health`-endepunktet i appen er uendra.

**Merk:** at oppgåva faktisk held servicen tilbake, og at ho forsvinn når handlinga er køyrd, er ei åtferd i StartOS som berre bokstesten i §32.8 punkt 7 kan stadfeste. SDK-en kallar henne ein «task notification», og det finst ikkje noko eige vilkår for «adminpassordet er ikkje sett» i SDK 3.0.4 (`TaskCondition` har berre `'input-not-matches'`), so oppgåva blir heva og lukka av init-skriptet og ikkje av eit vilkår.

Unngå: Postgres, Redis, ekstern backend, ekstern cloud-service for appdata, og ekstra container utan konkret behov.

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 14. Lagring og backup

- SQLite-database skal liggje på persistent volum.
- Appdata skal overleve restart.
- Konfigurer StartOS backup av persistent data.
- Test backup og test restore.
- Verifiser at gamle health checks finst etter restore.

**Merk:** alle punkta er køyrde og verifiserte på boksen, gjennom §16 StartOS-testen og §17. `startos/backups.ts` brukar `sdk.Backups.ofVolumes('main')`, og databasen ligg på `main`-volumet på `/data`. StartOS stoppar servicen medan ein backup går, så databasefila er ikkje under skriving når ho blir kopiert — ingen eigen SQLite-snapshot-krok trongst, og inga kjend avgrensing står att. Punkta skal køyrast på nytt når §32 er ferdig, sidan skjemaet og innlogginga har endra seg.

---

# 15. Sikkerheit og personvern

- Ingen seed phrase, private keys, wallet-passord eller sky-tokens i databasen.
- Ingen unødvendige personopplysningar. Kontaktinfo blir berre registrert som status (`Confirmed current` / `Needs external update`).
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.
- Ikkje implementer eigen kryptografi. Adminpassordet brukar `hashlib.scrypt` frå standardbiblioteket, og sesjonen ein HMAC-SHA256-signatur.
- Ikkje send data til eksterne tenester.
- Adressestien er ein offentleg derivasjonssti og inneheld inga hemmelegheit.
- Fritekst blir sjekka lokalt i `secret_guard.py` før lagring, og før lengdegrensa til feltet. Eit felt som ser ut som ei wallet-løyndom, blir avvist med `400`, ingenting blir lagra, og meldinga gjentek aldri verdien. Sjekken gjer ingen nettverkskall. Han er ei sperre mot dei vanlegaste formata, ikkje eit vern: eit nakent 64-teikns heks-streng, ei frase på eit anna språk, og ei løyndom delt over fleire felt, blir ikkje fanga. I UI-et står den korte åtvaringa **éin gong**, i nøkkeloppsettet, med stilen `.secret-warning`; ho blir ikkje gjenteken ved kvart fritekstfelt (§12 og §32.2 punkt 10). Serveren er uendra og avviser framleis eit løyndom i kvart fritekstfelt.
- Innlogginga er avgrensa: fem mislukka forsøk på rad låser innlogginga i 15 minutt med `429`. Teljaren ligg i `app_settings`, er ikkje knytt til IP, og appen les medvite ikkje `X-Forwarded-*`, sidan StartOS proxyar alt (§32.8 punkt 2).
- Eit `python3`-probe i pakka les `app_settings` i appdatabasen **readonly** for å sjå om ein admin finst (§13). Det skriv ingenting, gjer ingen nettverkskall, og sender ingenting vidare.

---

# 16. Testing

## Funksjonstest

- Opprett nøklane, start ein health check, fullfør alle kontrollpunkt, lagre han og vis han i historikken.
- Start ein ny health check, og verifiser at den gamle kontrollen framleis finst.

## Problemtest

- Test nøkkel utilgjengeleg, hardware-feil og seed-backup-feil.
- Test adressestifeil, både påminninga før innsending og varselet etterpå.
- Test programvare-inkompatibilitet, og at `Hardware works` og kontaktstadfestinga krev eit val.
- Test KI-status `VULNERABLE` og `COMPROMISED`, og kontaktinfo `Needs external update`.
- Test rotering av ein nøkkel, med og utan nytt namn, og at rotering krev ein ny adressesti.
- Test kvittering av eit varsel, og at eit nyare varsel kjem tilbake.
- Test at ein nøkkel med eit ope varsel ikkje kan få ein ny kontroll, og at nøkkelen blir ledig igjen når varselet er lukka.
- Test at to nøklar ikkje kan ha same adressesti, korkje i oppsettet, i innstillingane eller ved rotering, òg når den andre er skriven med `h`-markøren.
- Test kvar varselhandling, og at eit varsel utan handlingar blir rekna som ein feil.
- Test at eit nøkkelkort viser ei varselmelding når nøkkelen har eit ope varsel.
- Test at fjerning av den feilande programvara lukkar `software_incompatible`.
- Test at eit lukka varsel viser seg i historikken og i CSV-en, med handling og dato.
- Test at eit kontaktvarsel gir `Needs action` og sperrar nøkkelen, og at nøkkelen blir ledig att ved `contact_updated`.
- Test at `software_incompatible` med ei cloud-nøkkel-programvare gir `replace_hardware` på den kontrollerte nøkkelen, og at det same varselet frå innstillingslista held fram med `remove_software`.
- Test at ein kan byte namn på ein nøkkel i roteringsseksjonen utan å rotere han, og at ei rotering krev stadfestingsboksen.
- Test at ei rotering kan gi nøkkelen den andre typen, og at eit namn som wallet-programvare-lista alt har, blir avvist.
- Test innlogging og sesjon: første oppstart utan admin, rett og feil passord, `401` på API utan sesjon, omdirigering på sider, open `/health`, og eit manglande CSRF-token.
- Test at eit fritekstfelt som ser ut som ei wallet-løyndom, blir avvist, at meldinga seier kva ho ser ut som, og at ingenting blir lagra eller eksportert.
- Test at ein CSV-celle som byrjar med `=`, `+`, `-`, `@` eller eit kontrollteikn, blir eksportert som tekst, og at vanleg innhald er uendra.
- Test oppsett av eit annet multisig-oppsett enn 2-av-3, modell/teneste per nøkkel, det daterte eksportnamnet, sletting av all data, og installasjon av PWA-en.
- Test at `/robots.txt` blir svara, at kvar av dei seks sidene ber robots-metaen, og at kvart svar ber `X-Robots-Tag`.
- Test menyen, at sida ein står på er gråa ut og ikkje kan klikkast, at eksporten har sin eigen seksjon på history-sida med noten under lenkja, og at både `View` og ei innsending landar på `#history-detail`.
- Test at ein kontroll-dato i framtida blir avvist med `400`, og at dagen i dag og ein eldre dato går gjennom (§32.8 punkt 3).
- Test at fem feila innloggingsforsøk låser innlogginga i 15 minutt med `429`, at eit rett passord i låseperioden òg blir avvist, og at eit vellukka innlogging nullstiller teljaren (§32.8 punkt 2).
- Test at ei rotering legg til ei ny rad i `keys` med same `key_number`, at den gamle rada blir inaktiv, og at eldre kontrollar held på namnet og typen dei vart lagra med (§32.8 punkt 5).
- Test at ein cloud-nøkkel med `COMPROMISED` ikkje får eit nytt programvarevarsel når nøkkelen blir rotert eller omdøypt, og at lukka programvarevarsel viser seg i historia og i CSV-en (§32.8 punkt 6).

**Merk:** dei manuelle nettlesartestane er køyrde og verifiserte fram til §31. §32 legg til nye manuelle punkt: ikonet (32.1), UI-pussen og retro-temaet på ein smal telefon (32.2), og ein kikk på varsellista, nøkkelkortet og sperre-noten i skjemaet etter tekstendringane i 32.3. Etter runden 32.1/32.2 kjem òg: footeren på ei kort side, faviconet i fana, merket i topplinja, installasjon av PWA-en med dei to PNG-ikona, og history-visninga med dei tre tabell- og linjeendringane. §32.7 la til menyen i topplinja og det rydda dashbordet, med `Download CSV` og noten i sin eigen `Export`-seksjon på history-sida, og hoppet til `#history-detail`. §32.8 legg til den manuelle ende-til-ende-gjennomgangen i punkt 7, og dei nye manuelle punkta: at appen ikkje startar før adminpassordet er sett (punkt 1), at innlogginga blir låst etter fem feil forsøk (punkt 2), at ein framtidsdato blir avvist (punkt 3), at topplinja held seg på plass (punkt 4), at ei rotering ikkje endrar eldre historikk (punkt 5), og at lukka programvarevarsel står i historia og i CSV-en (punkt 6).

## StartOS-test

- Installer `.s9pk` på StartOS 0.4.0, start servicen og opne web UI.
- Utfør ein komplett test-check.
- Restart servicen, og verifiser at data framleis finst.
- Ta backup, restore backup, og verifiser data etter restore.
- Verifiser at `Set Admin Password` og `Delete all data` står i `Actions & Config` og verkar.
- Verifiser at ein installerbar PWA kan leggjast til frå nettlesaren.

**Merk:** alle er køyrde og verifiserte på boksen. `vardkey_x86_64.s9pk` vart sideloda og installert, servicen står som `Running`, helsesjekken melder «The web interface is ready», og `Open UI` opnar VardKey i nettlesaren på StartOS-adressa. Restart og restore heldt på dataa, og dei gamle health checkane fanst etter restore. Skal køyrast på nytt når §32 er ferdig.

---

# 17. Ferdigkriterium for første release

Før første release skal alle desse vere oppfylte:

- Appen køyrer på StartOS 0.4.0.
- Nøklane i multisig-oppsettet er representerte i appen.
- Ein komplett årleg health check kan gjennomførast i nettlesaren, og alle årlege kontrollpunkt kan registrerast.
- KI-status kan registrerast som SECURE, PATCHED, VULNERABLE eller COMPROMISED.
- Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- Problem gir tydelege varsel, og eit varsel kan lukkast på den måten som høyrer til varselet.
- Neste sjekk blir lagra, og historikk fungerer.
- CSV-rapport kan eksporterast.
- Data overlever restart, og backup og restore fungerer.
- Ingen wallet-hemmelegheiter blir lagra.
- Appen er passordbeskytta med ein adminbrukar.
- All appdata kan nullstillast frå StartOS, medan adminbrukaren står att.

**Merk:** alle punkta er køyrde og verifiserte på boksen. Kriterielista er oppfylt, men pakkeversjonen blir ikkje heva før §32 er ferdig — sjå §32.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- 1–8. Grunnleggande web-app, SQLite og datamodellen, nøklane, health check-skjemaet, lagring og historikk, varsellogikken, dashboardet og rapporteksport.
- 9. Implementer StartOS package.
- 10. Implementer persistent storage og backup.
- 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** steg 1–11 er ferdige. Steg 12 ventar på §32.

**Testar:** køyr `python3 -m unittest discover -s tests`. Suiten skal vere grøn både på Linux og på Windows-kopien.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# Reglar som gjeld alle rundar

Desse er bindande for kvar framtidig endring, ikkje berre for éin runde.

- **Migreringar er additive, eller ein ombygging etter mønsteret i §21.** Kvar migrasjon skal ha ein test med eit bokstaveleg eldre skjema (`SCHEMA_VERSION_n` i `tests/test_database.py`), og `PRAGMA foreign_key_check` før commit der ein tabell blir bygd om.
- **API-et held namna sine.** Nye felt kjem i tillegg; eksisterande felt byter ikkje namn eller type. Eit felt som forsvinn, er eit brot.
- **Ei eldre database skal alltid kunne opnast** og bli migrert framover. Appen skal framleis **nekte** å opne eit skjema som er nyare enn han sjølv kjenner, i staden for å skrive i det.
- **Pakkeversjonen rører ikkje appdata.** Appen migrerer skjemaet sitt sjølv ved oppstart, så `startos/versions/` treng inga datamigrering. Kjem det ein pakkeendring som krev det, skal `up`/`down` skrivast der — ikkje i appen.
- **Ein nedgradering til ein eldre pakkeversjon er ikkje støtta** når skjemaet har gått framover, og det skal stå i `UPDATING.md`.
- **Backup teken på ein eldre versjon** skal kunne gjenopprettast og bli migrert framover.
- **Eksporten er ein avtale.** Kolonnenamna i CSV-en blir ikkje endra utan at det står her eller i ein seinare runde.
- **Ingen indeksering og ingen bots.** Alle seks sidene ber `<meta name="robots" content="noindex, nofollow">`, `_send_security_headers()` i `app.py` legg `X-Robots-Tag: noindex, nofollow` på kvart svar, og `static/robots.txt` svarar `Disallow: /`. Robots-fila står i `STATIC_FILES`, men er **ikkje** i `SHELL`-lista i `static/sw.js`, sidan ho ikkje er ein del av app-skalet. Ein ny side skal ha metaen med frå første stund.
- **Navigasjonen ligg i topplinja, ikkje på sida.** `static/session.js` byggjer menyen på dei fem app-sidene, og sida brukaren står på er ikkje ei lenkje. Dashbordet skal ikkje ha navigasjonslenkjer i markupen sin, og eksporten ligg på history-sida.
- **Forbodslistene i §1 og §13 skal stadfestast på nytt før release.**

---

# 19–31. Historikk (ferdige og verifiserte)

Alle rundane under er implementerte og verifiserte. Reglane deira ligg i §1–§18 og i `ai-note.md`; den fulle grunngjevinga ligg i git-historikken. Detaljane er ikkje gjengjevne her, sidan ingen av dei er opne lenger.

| Runde | Kva han gjorde |
|---|---|
| §19 | Registrering per nøkkel: éi innsending gjeld éin vald nøkkel, og kvar nøkkel har sitt eige neste-sjekk-intervall. |
| §20 | Eit felt som ikkje gjeld for den valde nøkkelen eller programvara, blir skjult og utleidd, og alt utleidd blir lista i Review-oppsummeringa. |
| §21 | Engelske statusverdiar (`IKKJE_VURDERT` → `NOT_ASSESSED`) og `GET /api/alerts`, som summerer alle lagra kontrollar og listar kritiske først. Skjema 11. |
| §22 | Ein nøkkel som ikkje kunne kontrollerast, registrerer ingenting elles: `wallet_software` blir `NULL`, `software_compatibility_status` blir `NOT_ASSESSED`, og eit innsend resultat er ein `400`. |
| §23 | Konfigurerbart nøkkeloppsett ved første oppstart; `GET`/`POST /api/setup`. |
| §24 | Obligatoriske val (`Hardware works`, kontaktstadfestinga) og skjemastrukturen i seks seksjonar. BIP327/SLIP39 og `tool_checks` fjerna. |
| §25 | Adressestien som identitet, rotering, varselkvittering og innstillingar. |
| §26 | Sperring av ein nøkkel med ope varsel (`409`), unike adressestiar, og eigne lukkehandlingar per varselkode. |
| §27 | Varselhandlingane i historikk og CSV, kontaktvarselet som eit nøkkelvarsel, og dei to formene av `software_incompatible`. Skjema 11. |
| §28 | Nøkkeltypen kan berre endrast ved ei rotering, og namnet blir endra i roteringsseksjonen. Frå §32.8 legg ei rotering til ei ny rad i `keys` og pensjonerer den gamle, i staden for å skrive om henne. |
| §29 | Namnebyte til **VardKey**, med beskrivinga «Bitcoin Multisig Health Monitor», databasefila `data/vardkey.sqlite3` og eksportfila `vardkey-export.csv`. |
| §30 | StartOS 0.4.0-pakka: `id: 'vardkey'`, `volumes: ['main']`, `GPL-3.0-only`, bygd og verifisert på boksen. Pakkeversjonen startar på `0.1.0:0`. |
| §31 | Dei sju punkta før versjon 1: fleksibel terskel (skjema 12), modell/teneste per nøkkel, adressestien på nøkkelkortet, datert CSV-namn, sletting av all data, adminpassord med sesjon og CSRF, og ein installerbar PWA utan offline-data. |

---

# 32. Det som står att

Att står **§32.8 punkt 7**, **§32.6 dokumentasjonsdrifta** og **§32.5 hevinga av pakkeversjonen**, i den rekkjefølgja, og alle **før** pakkeversjonen blir heva frå `0.1.0:0` til `1.0.0:0`. §32.1–§32.4 og §32.7 er utførte og verifiserte, og står nedanfor som korte punktlister, slik at §-referansane i koden held. Eit punkt skal ikkje startast utan at brukaren ber om det.

**Status i §32:** §32.1 (ikonet), §32.2 (UI-passet med retro-temaet), §32.3 (varsel- og sidetekstane), §32.4 (bug-rapporten, rundane 32-A og 32-B) og §32.7 (dashboard-menyen og oppryddinga i dashbordet) er utførte, kvar med etterrunden sin. I §32.4 står berre **BR-003** att, og han er ei manuell ende-til-ende-verifisering som berre brukaren kan gjere — han er no punkt 7 i §32.8. I §32.8 er **steg A** (punkt 3, 4 og 2), **steg B** (punkt 1) og **steg C** (punkt 6 og 5) utførte, so skjemaet er no **versjon 13**; att står berre **punkt 7**. §32.8 skal gjerast ferdig før §32.6, som skal skildre den utgåva som faktisk blir gitt ut, og §32.5 kjem til slutt. Den manuelle nettlesartesten av retro-temaet på ein smal telefon står att for brukaren, saman med dei nye manuelle punkta i etterrunden av §32.1 og §32.2, menyen og det rydda dashbordet, installasjonen av PWA-en med dei to PNG-ikona, dei nye manuelle punkta i §32.8, og den nye bokstesten i §32.5.

## 32.1 Ikonet — utført

1. `icon.svg` i repo-rota og `static/icon.svg` er den same retro-teikninga: eit heva grått vindauge med dei tre nøklane, sentrerte i flata. Den marineblå tittelstripa er borte, nøkkelgruppa er 21 høg, flata innanfor 3D-kanten går frå 6 til 122, så senteret er 64 og nøklane står på `translate(23, 25.5)`, `(23, 51.5)` og `(23, 77.5)`. Fila i rota er 1,2 KiB, og ho er rein SVG utan fontar, bilete eller nettverkskall, så CSP-en `default-src 'self'` held.
2. Kvart av dei seks sidene har `<link rel="icon" type="image/svg+xml" href="/icon.svg">` i `<head>`, og `<img class="brand-mark" src="/icon.svg" alt="" aria-hidden="true">` i topplinja. Klassenamnet `brand-mark` står, og `.brand-mark` i `static/styles.css` er 18×18 med `image-rendering: pixelated`.
3. `static/icon-192.png` (192×192) og `static/icon-512.png` (512×512) er rasteriserte frå SVG-en. Begge står i `icons`-oppføringa i `static/manifest.webmanifest` med rett storleik og `type: "image/png"`, **etter** SVG-oppføringa, og begge er med i `STATIC_FILES` i `app.py` og i skal-allow-lista i `static/sw.js`.
4. `tests/test_pwa.py` pinnar favicon-lenka og merket på alle seks sidene, `.brand-mark`-stilen, at dei to SVG-filene har same teikning, at kvar PNG er den storleiken han oppgjev, og at begge blir serverte.

## 32.2 UI-finpussen — utført

Retro-temaet (Windows-app, midten av 90-talet) ligg i `static/styles.css`: bakgrunn `#c0c0c0`, felt `#ffffff`, mørk kant `#808080`, mørkast `#000000` og tittelstripe `#000080` med kvit tekst. Ingen `border-radius`, ingen `box-shadow` og ingen gradientar — djupna kjem av 3D-kantar. Skrifta er systemfont-stabelen `"MS Sans Serif", Tahoma, Verdana, Geneva, sans-serif` i 12–13 px, fokus er `outline: 1px dotted #000000`, og tabellane er rutemønster med 1 px rammer. `theme-color` på dei fem sidene og `/login` og `theme_color`/`background_color` i manifestet er `#c0c0c0`.

1. Luft mellom hjelpetekst og neste blokk: `.field-help + .field-grid, .field-help + .form-stack { margin-top: 12px; }`.
2. Åtvaringa mot å lime inn ei løyndom står no éin gong, som eitt `p.secret-warning` over heile nøkkel-lista i `setup.html`; `setup.js` legg henne ikkje lenger inn per kort.
3. Dashbord-overskrifta blir fylla av `renderSetupHeading()` i `app.js` frå `threshold` og `key_count` i `/api/setup`; linja i markupen er fallbacken.
4. «An overview of your multisig setup and annual checks.» er fjerna.
5. `section.setup-card` er fjerna, saman med `setupTitle`, `setupDescription` og `renderSetupShape()`.
6. Nøkkelkortet viser nummer og type på den øvste linja (`01 · Hardware`).
7. Nøkkelkortet viser berre stien, i skrå skrift (`.key-path`), utan prefikset `Address path:`.
8. Nøkkelkortet viser berre modellnamnet, under namnet og over stien, og hoppar over det når det berre gjentek nøkkelnamnet (`sameLabel()`).
9. Nøkkelkortet viser berre `Next check due`; `Last checked` er borte.
10. Den korte åtvaringa er fjerna frå `health-check.html`, `health-check.js`, `settings.js` og `setup.js`. Serveren er uendra: eit løyndom i eit fritekstfelt blir framleis avvist med `400`.
11. `Needs assessment`-lista i Review-oppsummeringa er fjerna; `Results requiring follow-up` står.
12. Oppsummeringslinja i Review med `Key N: … · Check date: … · Next check due: …` er fjerna.
13. `Local service` i topbaren og `Your data stays local.` i footeren er fjerna på alle sidene, òg `/login`.
14. Historikk-kortet viser datoen, nøkkelnummeret og namnet nøkkelen har no, og ein kort status (`All OK` / `Needs follow-up`). Dette kravde eit **additivt** felt i oppsummeringa: `GET /api/health-checks` gjev no `key_names` og `needs_follow_up` i tillegg til felta som alt var der (§11). `needs_follow_up` er ein eigenskap ved den lagra kontrollen, så han endrar seg ikkje når brukaren lukkar varselet seinare.
15. Historikk-tabellane held seg innanfor sida på ein smal skjerm, med `table-layout: fixed`, `overflow-wrap: break-word` og mindre skrift på `.detail-table`. Løyst i CSS, utan ny JavaScript.

Etterrunden av §32.1 og §32.2 — faviconet, merket, footeren og historia:

16. Footeren ligg nedst på sida òg når innhaldet er kort: `body` er ein kolonne med `min-height: 100vh` og `100dvh`, og `main { flex: 1 1 auto; }` tek resten.
17. Faviconet ligg på alle seks sidene.
18. Merket i topplinja er ikonet som bilete, med same klasse `brand-mark`.
19. «Back to dashboard» er fjerna frå `history.html`, `settings.html`, `setup.html` og `health-check.html`; merket «VardKey» er vegen tilbake. Lenkja i sperre-noten i skjemaet står.
20. «Start annual health check»-knappen er fjerna frå `history.html`. Ein kontroll blir starta frå dashbordet.
21. Historie-visninga i `history.js` slår saman programvara og versjonen hennar på éi line (`Sparrow Wallet 2.5.1`) og modellen og firmware-versjonen på éi line (`Blockstream Jade 1.4.1`); manglar ein del, står resten åleine, og manglar båe, står `—`. Lukke-tabellen viser `Alert`, `Action` og `Closed` — kjelde-kolonnen er borte. Dette kravde eit **additivt** felt i svaret: `GET /api/health-checks/<id>` ber no `model` på kvart nøkkelrecord (§11).

**Testar:** `tests/test_health_check_form.py`, `tests/test_pwa.py`, `tests/test_secret_guard.py`, `tests/test_key_status.py` og `tests/test_app.py` er oppdaterte. Suiten gjekk frå 477 til **484 testar**, etterrunden la til ti og PNG-ikona fire til, så han stod på **498 testar**.

## 32.3 Meldingstekstane i varsla — utført

1. Kvar av dei elleve varselradene i §7 har ein `message` i `alerts.py`, og alle er skrivne i same form: kva som er gale, kva nøkkel eller programvare det gjeld, og kva som lukkar varselet. `code`, alvor, kjelde, handlingar og `software`-feltet er uendra, og forma er no presisert i §7.
2. Meldinga gjentek ikkje namnet i `source`; ho seier «this key». Det einaste unntaket er den nøkkelforma av `software_incompatible` som namngjev programvara, fordi kjelda der er nøkkelen.
3. `_VULNERABLE_MESSAGE` og `_COMPROMISED_MESSAGE` er delte i kvar si melding for nøkkel- og programvareforma, sidan dei to formene blir lukka av kvar si handling. `_HARDWARE_FAILURE_MESSAGE`, `_SEED_BACKUP_MESSAGE` og malen `_SOFTWARE_INCOMPATIBLE_KEY_MESSAGE` er trekte ut av `_key_alerts`.
4. «Replace the key» er borte der den einaste handlinga er `rotate`, og «PROTOCOL 3: key loss» og «follow the key loss procedure» er tekne bort, sidan ingen av dei er definerte nokon stad.
5. Sperre-svaret (`409`) seier ikkje lenger den interne koden: «This key has an open alert. Close the alert before recording a new check.»
6. Sidetekstane som vart rydda: den dupliserte eyebrow-en i `index.html` og `settings.html`, den dupliserte `Sign in`-overskrifta i `login.html`, den dupliserte hjelpelinja og den døde `#software-help`-teksten i `health-check.html`, dei to `Removing an entry…`-hjelpene i `settings.html` slått saman til eitt avsnitt, «Open the settings» i både `setup.js` og `app.js`, og den gjentekne personvernsetninga i `app.js`'s `setupDescription`. `validation.py`-meldinga er skriven om til «this name already comes from a configured cloud key».
7. Medvite uendra: `ACTION_LABELS` / `ACTION_CONFIRMATIONS` i dei tre kopiane, og `UNAVAILABLE_MESSAGE` i `health-check.js`.

**Testar:** `tests/test_alerts.py` held tekstane; seks testar er oppdaterte eller omdøypte, og éin ny pinnar at nøkkelforma og programvareforma av same kode har kvar si melding. `tests/test_app.py` held ikkje på nokon meldingstekst.

## 32.4 Bug-rapporten — utført, utanom BR-003

Rapporten vart skriven mot eit anna filsett; dei åtte dokumenta han ber om finst ikkje her, og skal ikkje opprettast. Kvar BR vart verifisert i koden som ligg i dette repoet før noko vart endra:

- **BR-001 — falsk positiv.** Kjeldefilene ligg i `main` og er spora av Git; rapporten bygde på repo-visinga, ikkje på ein checkout.
- **BR-002 — stadfesta og retta** i runde 32-B, sjå nedanfor.
- **BR-003 — står att.** Sjå «Det som står att i 32.4» nedanfor. Han er no punkt 7 i §32.8.
- **BR-004 — fell bort.** `AI-STATUS.md` og `DATA-MODEL.md` finst ikkje i dette repoet, og koden følgjer alt kontrakten i §4–§7. Den reelle dokdrifta er 32.6.
- **BR-005 — verifisert i koden, inga åtferdsendring.** Berre `GET /health`, `GET /api/session` og `/login` er opne; alle andre `/api/*` svarar `401` og sidene `302` til `/login`; kvar tilstandsendrande POST krev økt og CSRF-token (`403`). Passordet er ein `hashlib.scrypt`-hash med salt per passord, økta ein HMAC-SHA256-signert cookie med utløp, og begge samanlikningane brukar `hmac.compare_digest`. `Secure`-flagget er medvite utelate, fordi StartOS terminerer TLS og proxyar rein HTTP inn i containeren.
- **BR-006 — retta i `export.py`.** Ei tekstcelle som byrjar med `=`, `+`, `-`, `@` eller eit kontrollteikn — òg etter leiande mellomrom — blir prefiksa med ein apostrof (§10).
- **BR-007 — retta i `static/sw.js`.** Tenestearbeidaren lagrar no eit svar berre når det er vellukka, same-opphav og ikkje omdirigert (§12).
- **BR-008 — retta i `validation.py`.** Samanlikninga av adressestiar fellar no òg den harda markøren (`h`/`H` ≡ `'`), i oppsettet, i innstillingane, ved rotering og i kontrollen. Den lagra verdien blir aldri skriven om (§4).

**Runde 32-B.** `secret_guard.py` avviser eit wallet-løyndom i kvart fritekstfelt med `400`, før noko blir lagra og før lengdegrensa til feltet; `auth.py` gjer det same for adminbrukarnamnet, men ikkje for passordet. Meldinga namngjev feltet og forma og gjentek aldri verdien. Sjekken er lokal og gjer ingen nettverkskall. Ordlista, mønstra og dei kjende avgrensingane står i modulens docstring. Reglane står òg i §2, §12 og §15.

**Testar:** ti i runde 32-A og 43 i den nye `tests/test_secret_guard.py` i runde 32-B. Suiten gjekk frå 422 til **484 testar**, og vidare til 498 etter etterrunden av §32.1 og §32.2.

**Det som står att i 32.4:** berre **BR-003**, og han må lesast rett. Rapporten siterer ein §31-tekst om at den manuelle gjennomgangen står att, men den teksten finst ikkje lenger, og §16 og §17 seier at dei manuelle nettlesartestane og bokstestane vart køyrde og verifiserte fram til §31. Det som faktisk står att, er difor dei **nye** manuelle punkta §32 legg til — ikonet, UI-pussen og retro-temaet på ein smal telefon, ein kikk på varsellista, nøkkelkortet og sperre-noten etter tekstendringane, menyen og det rydda dashbordet, og eksportseksjonen på history-sida — saman med heile bokstesten på nytt etter §32.5, og ei stadfesting frå brukaren på at dei er køyrde. Ikkje re-verifiser det §16 og §17 alt har som gjort. Punkta i BR-003 er førte opp som punkt 7 i §32.8.

## 32.5 Hevinga av pakkeversjonen

- Pakkeversjonen blir heva frå `0.1.0:0` til `1.0.0:0` når punkta over er ferdige og brukaren seier ifrå. §18 steg 12 («bygg endeleg `.s9pk` og gjer første release») høyrer til same runden.
- Inga skjemaendring, ingen nye endepunkt og ingen nye funksjonar i denne runden. `startos/versions/` held fram tomt for datamigrasjonar, sidan appen migrerer skjemaet sitt sjølv.

## 32.6 Dokumentasjonsdrifta

Dokumenta som skildrar pakka og appen, er skrivne før §31 og før 32-A, 32-B og 32.2, og dei er framleis ikkje oppdaterte. Dette punktet rettar dei. Det må gjerast **etter** 32.1–32.3, 32.7 og 32.8 og **før** 32.5, slik at dokumenta skildrar den utgåva som faktisk blir gitt ut, og det svarar samstundes på resten av BR-004 i bug-rapporten. Etter §32.7 manglar dokumenta i tillegg menyen i topplinja, at dashbordet ikkje har `Next check`-kortet og history-blokka, at `Download CSV` og noten ligg i sin eigen `Export`-seksjon på history-sida, at menyen merkjer sida ein står på, hoppet til `#history-detail`, og robots-sperra. Etter §32.8 kjem òg: admin-steget og pakkeoppgåva som held servicen tilbake, `429`-låsinga av innlogginga, at ein kontroll-dato ikkje kan liggje i framtida, den faste topplinja, at ei rotering legg til ei ny nøkkelrad og at historia er frosen, at eit lukka programvarevarsel òg står i historia og CSV-en, og at skjemaet er **13**.

- `README.md` (pakke-README): «Actions: None» og `actions: []` i Quick Reference stemmer ikkje — pakka har to handlingar, `Delete all data` og `Set Admin Password`, og frå §32.8 ei påkravd oppgåve som held servicen tilbake til adminpassordet er sett. Fyrstegongsflyten manglar admin-steget, og «Limitations» manglar at terskel og nøkkeltal er valfrie (`2 ≤ key_count ≤ 15`), at databasen ligg ukryptert på volumet, og at fritekst blir sjekka lokalt. «The icon is a placeholder» er òg utdatert etter §32.1, og «a fixed 2-of-3 … the three keys» i innleiinga og i Limitations er utdatert etter §31 punkt 7.
- `docs/application.md` (app-referansen): API-tabellen manglar `GET /api/session`, `POST /api/admin`, `POST /api/login` og `POST /api/logout`, og han skildrar korkje innloggingsvakta (`401` på API, `302` til `/login` på sider, `403` utan CSRF-token, `429` ved låst innlogging) eller kva ruter som er opne. Han manglar òg formelnøytraliseringa i CSV-en, den kanoniske stisamanlikninga og den lokale sperra mot wallet-løyndomar, og setninga om at den manuelle StartOS-testen framleis står ope er utdatert. Etter 32.2 manglar han òg `key_names` og `needs_follow_up` i `GET /api/health-checks`, og skildringa av felta ved kvart fritekstfelt. Etter runden 32.1 manglar han `model` i `GET /api/health-checks/<id>`, favicon-lenka på sidene og dei to PNG-ikona med sine eigne stiar. «a fixed 2-of-3» i innleiinga og «the three key profiles» under «Current status» er òg utdaterte etter §31 punkt 7. Etter §32.7 manglar han robots-fila, robots-metaen, `X-Robots-Tag`, menyen i topplinja, at `Download CSV` og noten no ligg i sin eigen `Export`-seksjon på history-sida, og ankeret `#history-detail`. Etter §32.8 manglar han i tillegg skjema 13 og dei nye kolonnane, at ei rotering legg til ei ny nøkkelrad, at namnet og typen på ein kontroll kjem frå snapshottet på kontrollen, at lukka programvarevarsel òg blir lista, `429`-låsinga, datogrensa, den faste topplinja, og den påkravde oppgåva som held servicen tilbake til admin finst.
- `instructions.md`: manglar innloggingssteget, opprettinga av admin, dei to handlingane i `Actions & Config` og den påkravde oppgåva frå §32.8 punkt 1. «exactly three keys … another threshold is not supported» er feil etter §31 punkt 7.
- `UPDATING.md`: seier skjema **11**; det er **13** etter §32.8. Versjoneksempla og tag-regelen skal framleis stå, og modullista bør nemne `auth.py`, `maintenance.py` og `secret_guard.py`.
- `AGENTS.md`: modullista nemner ikkje `auth.py`, `maintenance.py` eller `secret_guard.py`, og testavsnittet nemner ikkje at suiten òg dekkjer sperra. Etter §32.8 bør han òg nemne `startos/init/requireAdmin.ts` og den påkravde oppgåva.
- `startos/manifest/i18n.ts` og `startos/i18n/dictionaries/`: kort- og langskildringa seier «a fixed 2-of-3 … the three keys» på fem språk. Skal ordlyden bli «eit multisig-oppsett, 2-av-3 som standard», må alle fem språka skrivast om, og `make x86` køyrer `prettier --check startos`.

Ikkje bygg om overskriftstrukturen i `README.md` (han følgjer rettleiinga), og ikkje legg til nye dokument. Dei åtte filene bug-rapporten nemner (`SECURITY.md`, `PRIVACY.md`, `THREATMODEL.md`, `PLATFORM-ACCESS.md`, `ENCRYPTION.md`, `OFFLINE.md`, `AI-STATUS.md`, `DATA-MODEL.md`) skal **ikkje** opprettast. Dokumenta i repoet er `README.md`, `docs/application.md`, `instructions.md`, `UPDATING.md`, `AGENTS.md` og `TODO.md`.

## 32.7 Dashboard-menyen og oppryddinga i dashbordet — utført

Seks punkt, inga skjemaendring, ingen nye endepunkt, ingen nye funksjonar, og `static/robots.txt` var den einaste nye fila. Runden vart utførd **før** 32.6 og 32.5, og §8, §9 og §12 skildrar no den nye sanninga, sidan §1–§18 skildrar appen slik han er no.

1. **Meny i topplinja i staden for «Sign out».** `static/session.js` byggjer ein `Menu`-knapp med nedtrekk på alle fem app-sidene (`/login` har framleis ingen). Vala, i denne rekkjefølgja: `Start health check` → `/health-check`, `Settings` → `/settings`, `History` → `/history`, så ein skiljelinje, og til slutt `Sign out`, som gjer det same som før (`POST /api/logout` gjennom den pakka `fetch`-en, deretter `/login`). `Sign out` er ein `<button type="button">`, dei tre andre er `<a>`. Panelet er skjult som standard og blir opna og lukka ved klikk, med `aria-haspopup`, `aria-expanded` og `aria-controls`, og det blir lukka på `Escape`, ved klikk utanfor og etter eit val. `session.js` held fram med å lage `.topbar-actions`-innpakninga si sjølv. **Fjerna frå `static/index.html`:** `<a class="primary-button active-button" href="/health-check">Start annual health check</a>` i `.page-heading` og heile `<div class="topbar-actions">` med `Settings`-lenkja. **Behalde:** lenkja til `/` i sperre-noten i `health-check.html`, «Open the settings» i `setup.js`, `/settings`-lenkjene i `app.js` og «Open the alert list» på nøkkelkortet — dei er kontekstlenkjer, ikkje navigasjon. Nye klassar i `static/styles.css` (`.menu`, `.menu-button`, `.menu-panel`, `.menu-item`, `.menu-separator`), i retro-temaet og utan inline stil, fordi CSP-en er `default-src 'self'`.
2. **«Configured setup / Your keys» og nøkkelteljaren bort.** `section.section-block` som bar eyebrow-en `Configured setup`, `h2` «Your keys» og `span#key-count` er sletta frå `static/index.html`, og `<div class="key-grid" id="key-list">` står no rett etter `<p class="intro" id="setup-shape">`, inne i den same `section.page-heading`. `aria-labelledby="keys-title"` fell bort. I `static/app.js` er `const keyCount` og båe skrivingane til han sletta, så ingen `querySelector` peikar på eit element som ikkje finst.
3. **«Next check»-kortet bort, tidlegaste forfall inn i «Attention».** `.info-card`-et med `#next-check-title` og `#next-check-detail` er sletta, og «Attention»-kortet står att åleine og spenner heile innhaldsbreidda; `.overview-grid` er éin kolonne på alle breiddder. `nextCheckTitle` og `nextCheckDetail` er borte frå `static/app.js`, og `renderSummary()` styrer berre «Attention»: overskrifta er uendra (`Nothing overdue` / `1 key overdue` / `N keys overdue`), detaljlinja er den forfalne lista når noko er forfalle, og elles `Earliest next check <YYYY-MM-DD>, for Key N: <namn>.` Har ingen nøkkel ein `next_check_due`, står fallbacken `No key has a next check date yet. Save a health check to schedule one.`
4. **Tomt varsel-område utan plasshaldartekst.** `renderAlerts()` i `static/app.js` tømmer `#alerts-list` utan tekst når det ikkje finst varsel, medan `alertCount` held fram med `No alerts`. `aria-live="polite"`-regionen, plasshaldaren i markupen og feilgreina står uendra.
5. **History-blokka bort frå dashbordet, `Download CSV` til history-sida.** `section.history-card` i `static/index.html` er sletta. I `static/history.html` kom `<a class="secondary-button" href="/api/export">Download CSV</a>`, **utan** `download`-attributt, så filnamnet frå `Content-Disposition` vinn. Den daude `history-card`-delen av selektoren i `static/styles.css` er fjerna.
6. **Ingen indeksering, ingen bots.** Ny `static/robots.txt` med `User-agent: *` og `Disallow: /`, lagt inn i `STATIC_FILES` i `app.py` som `text/plain; charset=utf-8` (ei fil som ikkje står der, svarar `404`), men **ikkje** i `SHELL`-lista i `static/sw.js`. `X-Robots-Tag: noindex, nofollow` blir lagd i `_send_security_headers()` i `app.py`, så sider, JSON, redirect, CSV og statiske filer er dekte i éin stad. Alle seks sidene i `static/` fekk `<meta name="robots" content="noindex, nofollow">` i `<head>`.

**Bindingar:** engelsk UI-tekst og engelske kommentarar; CSP-en `default-src 'self'; style-src 'self'; script-src 'self'` tillèt ikkje inline skript eller inline stil; retro-temaet i §32.2 tillèt ingen `border-radius` utanom `0`, ingen `box-shadow` og ingen gradient. `alerts.py`, `validation.py`, `secret_guard.py`, `auth.py`, `database.py`, `export.py`, `maintenance.py`, ikonet, manifestet, `sw.js`, `startos/` og pakkeversjonen er ikkje rørde.

**Testar:** kvar streng og kvar selektor som vart fjerna eller omdøypt, vart greppa i `tests/` først, og ingen påstand vart sletta utan å bli erstatta av ein som pinnar den nye åtferda. Tretten nye testar pinnar menyen, at dashbordet ikkje har dei fjerna elementa, earliest-linja i «Attention», den tome varsellista, `Download CSV`-lenkja på history-sida utan `download`, robots-metaen på alle seks sidene, `/robots.txt`, og `X-Robots-Tag`-headeren. Suiten gjekk frå 498 til **511 testar**.

Etterrunden (fire punkt frå brukaren sin gjennomgang), utan skjemaendring, utan nye endepunkt og utan nye dokument:

1. **Eksport-noten flytt til history-sida.** `p#workflow-note` vart fjerna frå `static/index.html` og stod no i `static/history.html`, rett under `Download CSV`-lenkja, med ny ordlyd: «Download CSV exports every saved key check, one row per key check, as a dated file.» `static/styles.css` fekk `.page-heading > .secondary-button { margin-top: 12px; }`, så knappen ikkje rører linja over seg.
2. **Menyen: `Dashboard` fyrst, og sida ein står på er gråa ut.** `MENU_ITEMS` i `static/session.js` har fire oppføringar: `Dashboard` → `/`, `Start health check` → `/health-check`, `Settings` → `/settings`, `History` → `/history`. Sida brukaren alt står på blir rendra som eit `<span class="menu-item menu-item-current">` med `aria-current="page"` i staden for ein `<a>`, så ho kan ikkje klikkast og sida blir ikkje lasta på nytt. Samanlikninga normaliserer stien (`/health-check/` ≡ `/health-check`, rota blir `/`). `.menu-item-current` er grå (`var(--line)`) med `cursor: default`, og hover-/fokus-regelen er avgrensa med `:not(.menu-item-current)`.
3. **Ankeret `#history-detail`.** `View`-lenkja i `history.js` peikar no på `/history?id=<id>#history-detail`, og `health-check.js` sender brukaren til `/history?id=<ny id>#history-detail` etter lagring. Sidan detaljen er skjult til ein kontroll blir opna, og eit skjult element ikkje har nokon boks å rulle til, avdekkjer den nye `revealDetail()` seksjonen først og kallar `scrollIntoView({ behavior: "smooth", block: "start" })` etterpå.
4. **Eksporten fekk ein eigen seksjon, og `id="workflow-note"` er borte.** `Download CSV`-lenkja står ikkje lenger laus i `.page-heading`; ho har ein eigen `section.section-block` i `static/history.html`, mellom lista og detaljseksjonen, med eyebrow-en `Export`, tittellinja `<h2 id="export-title">Download the report</h2>`, lenkja og noten rett under henne. Noten har framleis klassen `workflow-note` men ingen `id`, og ordlyden er «Every saved key check is exported, one row per key check, as a dated CSV file.». Sidan lenkja ikkje lenger står i sideoverskrifta, er CSS-regelen `.page-heading > .secondary-button` fjerna som daud.

**Testar i etterrunden:** to testar er omdøypte og utvida i staden for sletta — `test_the_top_bar_menu_offers_the_three_pages_and_sign_out` → `test_the_top_bar_menu_lists_the_dashboard_and_the_pages`, og `test_the_history_page_offers_the_export` → `test_the_history_page_offers_the_export_and_the_note` → `test_the_history_page_offers_the_export_in_its_own_section`. To nye kom til: `test_the_menu_marks_the_page_you_are_on_and_greys_it_out` og `test_the_history_links_to_the_detail_section`. I tillegg pinnar `test_the_dashboard_has_no_next_check_card_and_no_history_block` no `<p class="eyebrow">Next check</p>` i staden for den bare frasen `Next check`, fordi ein bar delstreng òg fangar ein HTML-kommentar. Suiten går frå 511 til **513 testar**, og talet står framleis på 513 etter det siste punktet, sidan det berre døypte om ein test.

## 32.8 Sju punkt før 32.5 og 32.6

**Utførast før §32.6 og §32.5**, i denne rekkjefølgja: **steg A** (punkt 3, 4 og 2), **steg B** (punkt 1), **steg C** (punkt 6 og 5 saman, sidan begge krev skjema **13**), og til slutt **punkt 7**, som berre brukaren kan gjere. Inga nye endepunkt utanom den nye feilkoden `429`, inga ny avhengigheit, ingen nye dokument, og inga endring i CSV-avtalen utanom det som står i punkt 6.

**Status:** **steg A** (punkt 3, 4 og 2), **steg B** (punkt 1) og **steg C** (punkt 6 og 5) er utførte. Att står berre **punkt 7**, som berre brukaren kan gjere.

- [x] **1. Appen skal ikkje starte før adminpassordet er sett.** Pakka skal halde servicen tilbake til admin finst: ei påkravd StartOS-oppgåve (task) som køyrer `maintenance.py set-admin-password` i ein `withTemp`-subcontainer, og som StartOS ikkje lèt brukaren hoppe over. Passordet blir framleis generert **inne i containeren** og skrive ut éin gong — ingenting går frå verten inn i containeren som argument eller på stdin, slik at den eksisterande tryggleiksmodellen held. `startos/main.ts` sin readiness-sjekk mot `/health` står uendra. På app-sida er gatinga som alt finst nok: utan admin svarar `/api/*` `401`, sidene svarar `302` til `/login`, og `/login` viser berre loginsteget og opprett-admin-skjemaet. Det skjemaet er **den lokale bootstrapen** for `python3 app.py`, og blir verken utvida eller fjerna i denne runden; i pakka er han uoppnåeleg fordi servicen ikkje køyrer. Risiko: task-API-et i `@start9labs/start-sdk` 3.0.4 må stadfestast mot SDK-en eller pakkeleiingi før det blir brukt; kan det ikkje stadfestast, blir berre app-sida gjord ferdig, og det blir rapportert. `make x86` køyrer brukaren. **Utført**: task-API-et vart stadfesta mot dei publiserte typane i 3.0.4 (`sdk.action.createOwnTask` / `createTask` / `sdk.action.clearTask`, `effects.action.clearTasks`, `TaskSeverity = 'optional' | 'important' | 'critical'`, `createTask` svarar `null`) og mot SDK-en si eiga `setupPrimaryUrl.setupTask`-implementering. `startos/init/requireAdmin.ts` held oppgåva `Set Admin Password` oppe med `severity: 'important'` medan databasen ikkje har nokon admin, og lukkar henne att når han finst. Oppgåva peikar på den eksisterande handlinga. Sidan SDK 3.0.4 berre har `TaskCondition = 'input-not-matches'`, finst det ikkje noko vilkår for «adminpassordet er ikkje sett», so heving og lukking skjer i init-skriptet. Proben som les `app_settings` (readonly, i ein `withTemp`-subcontainer) **feilar ope**. `tsc --noEmit`, `prettier --check startos` og `make x86` er grøne hjå brukaren. **At oppgåva faktisk held servicen tilbake, og forsvinn når handlinga er køyrd, er framleis ustadfesta og ligg i punkt 7.**
- [x] **2. Avgrensing av feila innloggingsforsøk.** Etter **5** mislukka `POST /api/login` på rad blir vidare innloggingar avviste i **15 minutt** med den nye statuskoden `429` og ei melding som seier kor lenge det står att. Eit rett passord i låseperioden blir òg avvist, så svaret røpar ikkje om passordet var rett. Ei vellukka innlogging nullstiller teljaren. Teljaren ligg i `app_settings` (`failed_login_count`, `failed_login_until`), så han overlever ein restart. Inga IP-basert logikk: StartOS proxyar alt, og appen les medvite ikkje `X-Forwarded-*`. `POST /api/admin` (den lokale bootstrapen) blir ikkje avgrensa. `429` skal inn i feilkodelista i §11. **Utført** i `app.py` (`_login()` og hjelparane `lockout_seconds_left()`, `register_failed_login()`, `clear_failed_logins()`, `lockout_message()`), med `failed_login_count` / `failed_login_until` i §4 og `429` i feilkodelista i §11. Testar: fem feil → `429` på den femte, rett passord i låseperioden òg `429`, nullstilling ved vellukka innlogging, og at `POST /api/admin` ikkje blir avgrensa.
- [x] **3. Ingen kontroll-dato i framtida.** `checked_at` må vere dagens dato eller tidlegare. Grensa blir handheva på serveren i `validation.py` og gjev `400` med ei tydeleg melding, og date-feltet i skjemaet får `max` sett til dagens lokale dato i `health-check.js`. `next_check_due` er uendra (eitt kalenderår etter sjekkdatoen). §6 steg 1 blir oppdatert. **Utført** i `_date()` i `validation.py` og i `setCheckDate()` i `static/health-check.js`. Testar: i morgon → `400`, i dag og ein eldre dato → `201`.
- [x] **4. Topplinja fest til toppen.** `.topbar` i `static/styles.css` blir `position: sticky; top: 0` med ein `z-index` som held ho over sideinnhaldet og under meny-panelet, så ho blir verande synleg når ein scrollar. Utan inline stil (CSP), og utan `border-radius`, `box-shadow` eller gradient (retro-temaet i §32.2). §12 blir oppdatert. **Utført**: `.topbar` er `position: sticky; top: 0; z-index: 5`, og meny-panelet held sitt `z-index: 10`.
- [x] **5. Rotering gir ny nøkkelrad, og historia blir frosen.** Ei rotering skal ikkje lenger skrive om den eksisterande nøkkelrada. Ho legg til **ei ny rad** i `keys` med **same `key_number`** (multisig-plassen), den nye typen, den nye adressestien, namnet og modellen, og merkjer den gamle rada som inaktiv. Eldre kontrollar peikar framleis på den gamle rada, og kvar kontroll lagrar i tillegg eit **snapshot** av namnet, typen og modellen slik dei var då kontrollen vart lagra, så korkje ei rotering eller ei omdøyping kan endre eldre historikk. Krev **skjema 13**: `UNIQUE` på `keys.key_number` blir fjerna og erstatta av eit delvis unikt indeks på `key_number` der rada er aktiv, `keys` får eit aktiv-flagg og eit `rotated_at`, og `key_checks` får snapshot-kolonnane. Migreringa følgjer mønsteret i §21 (ombygging, `PRAGMA foreign_key_check` før commit, og ein test med eit bokstaveleg `SCHEMA_VERSION_12`), og backfyller snapshottet frå den kopla `keys`-rada, så eksisterande historikk held namnet han har ved migreringa. Alle spørringar som i dag les «nøkkelen» (`list_keys`, `list_key_status`, `list_previous_values`, oppsettet, innstillingane, skjemaet, dashboardet, roteringa) skal lese den **aktive** rada, medan historikk, CSV og varsel skal lese snapshottet. §4, §9, §10, §11 og §28 blir oppdaterte. **Utført** i `database.py` (`SCHEMA_VERSION = 13`, `KEYS_TABLE` med `active` og `rotated_at` og utan `UNIQUE` på `key_number`, det delvise indekset `idx_keys_active_key_number … WHERE active = 1`, snapshot-kolonnane i `KEY_CHECKS_TABLE`, `_migrate_keys()`, `_backfill_key_check_snapshots()`, `rotate_key()`, og `active = 1`-filteret i `list_keys()`, `list_key_status()` og `list_previous_values()`), i `app.py` (`_rotate_key()` kallar no `rotate_key()`, kvitteringane blir framleis skrivne på den gamle nøkkel-id-en, og `_send_health_check_list()` les `key_names` frå snapshottet på kontrollen), og i `database.py` sine lesarar for historikk og CSV (`get_health_check()` og `list_export_rows()` les snapshotet). §4, §9, §10, §11 og §28 er oppdaterte. Testar: `tests/test_database.py` har `SCHEMA_VERSION_12` med eit bokstaveleg eldre skjema og dekkjer snapshot-backfillen og det delvise indekset; `tests/test_app.py` pinnar at roteringa legg til ei ny aktiv rad med same `key_number` medan den gamle blir inaktiv, at ein kontroll kan registrerast på den nye rada, at historia er frosen etter både rotering og omdøyping, og at `key_names` kjem frå snapshottet; `tests/test_export.py` pinnar at ei eldre eksportrad held nøkkelnamnet og -typen sin.
- [x] **6. KI-kjelda kan ikkje flippe, og lukka programvarevarsel kjem i historia.** Kvar rad i `ai_security_checks` får `key_id` (nullable), sett til den kontrollerte nøkkelen når leverandøren er nøkkelen sitt eige konfigurerte namn. Då blir kjelda til eit KI-varsel avgjord av rada sjølv, ikkje av ei samanlikning med namna som er konfigurerte no, og ein cloud-nøkkel som blir rotert eller omdøypt kan ikkje lenger gi eit nytt programvarevarsel ved sida av det nøkkelvarsla som roteringa alt lukka. Samstundes skal lukka **programvarevarsel** òg visast i historia og i CSV-en, ikkje berre lukkingar som høyrer til ein nøkkel: `app.closed_alerts()` og `database._grouped_closures()` sluttar å filtrere på `key_id IS NOT NULL`, og lukkinga blir framleis knytt til kontrollen sin gjennom `check_id`. Krev skjema 13 (same migrering som punkt 5). §7, §9 og §10 blir oppdaterte. **Utført** i `database.py` (`ai_security_checks.key_id` i `AI_SECURITY_CHECKS_TABLE` og i `OPTIONAL_COLUMNS`, `save_health_check()` set han når leverandøren er nøkkelen sitt eige namn, og `_grouped_closures()` filtrerer berre på `check_id IS NOT NULL`), i `alerts.py` (`_security_alerts()` slår opp rada sin eigen `key_id` i staden for å samanlikne leverandøren med dei konfigurerte namna; `cloud_names` gjeld framleis `software_incompatible`) og i `app.py` (`closed_alerts()` filtrerer ikkje lenger, og docstringane i `_send_health_check_list()` og `_send_health_check()` seier det same som koden). §7, §9 og §10 er oppdaterte. Testar: `tests/test_alerts.py` byggjer KI-kjelda på rada si eiga `key_id` og pinnar at ein cloud-nøkkel med `COMPROMISED` ikkje får eit nytt programvarevarsel etter rotering eller omdøyping; `tests/test_app.py` pinnar at eit lukka programvarevarsel blir lista saman med eit lukka nøkkelvarsel; `tests/test_database.py` og `tests/test_export.py` pinnar at det står i siste kolonne i CSV-en.
- [ ] **7. BR-003 — den manuelle ende-til-ende-gjennomgangen.** Berre brukaren kan gjere denne, og ho blir ikkje rekna som gjord før brukaren seier det. Ho dekkjer: første oppsett og obligatorisk oppretting av admin; login og logout; utløpt eller ugyldig sesjon; direkte API-kall utan innlogging; ein full kontroll og CSV-eksport; ein alternativ terskel og eit anna nøkkeltal; sletting av data med stadfesting; restart, backup og restore; og PWA offline og online, òg etter logout. Punkta over legg til: at appen ikkje startar før adminpassordet er sett (punkt 1), at innlogginga blir låst etter fem feil forsøk (punkt 2), at ein framtidsdato blir avvist (punkt 3), at topplinja held seg på plass (punkt 4), at ei rotering ikkje endrar eldre historikk (punkt 5), og at lukka programvarevarsel står i historia og i CSV-en (punkt 6).

**Kva spec-seksjonar som må oppdaterast når punkta landar:** §4, §6, §7, §9, §10, §11, §12, §13 og §28, pluss skjemanummeret i §11, `UPDATING.md` og `AGENTS.md` (det siste høyrer til §32.6). §32.6 si liste skal nemne dei nye punkta.

**Testar:** kvar av punkta får regresjonstestar i same endring, og ein påstand blir aldri sletta utan å bli erstatta av ein som pinnar den nye åtferda. Nye testar dekkjer: datogrensa (`400` for i morgon, `201` for i dag og for ein eldre dato), innloggingslåsinga (fem feil → `429`, rett passord i låseperioden òg avvist, nullstilling ved vellukka innlogging), at roteringa legg til ei ny aktiv rad med same `key_number` og at den gamle rada blir inaktiv, at eldre kontrollar held snapshot-namnet sitt etter både rotering og omdøyping, at ein cloud-nøkkel med `COMPROMISED` ikkje får eit nytt programvarevarsel etter rotering, at lukka programvarevarsel viser seg i historia og CSV-en, og at topplinja er fest i stilarket. Migreringa frå skjema 12 får sin eigen test etter mønsteret i `tests/test_database.py`. Brukaren køyrer `python3 -m unittest discover -s tests` og oppgjev talet før og etter.

**Steg A — utført.** Punkt 3, 4 og 2 er landa i `validation.py`, `static/health-check.js`, `static/styles.css` og `app.py`, med nye testar i `tests/test_app.py` og `tests/test_health_check_form.py`. Sju testar i `tests/test_app.py` som lagra framtidsdatoar for å teste «nyaste kontroll vinn», vart flytte inn i fortida i same endring, sidan grensa no avviser dei. `§6`, `§11` og `§12` er oppdaterte. Suiten står på **519 testar**.

**Steg B — utført.** Punkt 1 er landa i `startos/init/requireAdmin.ts` (ny), `startos/init/index.ts`, `startos/i18n/dictionaries/default.ts` og `startos/i18n/dictionaries/translations.ts`, og §13 er oppdatert. Inga Python-fil og inga anna pakkefil er rørd, so Python-suiten står framleis på **519 testar**. `npx tsc --noEmit`, `prettier --check startos` og `make x86` er grøne. Det som står att av punkt 1, er bokstesten i punkt 7.

**Steg C — utført.** Punkt 6 og 5 er landa i `alerts.py` (KI-kjelda kjem frå rada), `app.py` (roteringa legg til ei ny rad gjennom `rotate_key()`, kvitteringane blir skrivne på den gamle rada, `closed_alerts()` filtrerer ikkje lenger, og `key_names` kjem frå snapshottet), `database.py` (`_grouped_closures()` filtrerer berre på `check_id`) og `export.py` (module-docstringen). Skjemaet er **13**. Att står berre punkt 7. Testane i `tests/test_alerts.py`, `tests/test_export.py`, `tests/test_app.py` og `tests/test_database.py` er oppdaterte: åtte testar i `tests/test_alerts.py` bygde KI-kjelda på dei konfigurerte namna og er skrivne om, tre påstandar som sa at eit lukka programvarevarsel ikkje blir lista er snudde, og sju nye testar kom til. `tests/test_key_status.py` og `tests/test_health_check_form.py` vart grepa for kvar streng dei pinnar og trong inga endring, sidan inga fil dei les vart rørd. Suiten går frå **519** til **526 testar**, og brukaren stadfestar talet ved å køyre `python3 -m unittest discover -s tests` på Linux og på Windows-kopien.
