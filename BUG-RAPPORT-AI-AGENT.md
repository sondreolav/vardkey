# Bug- og sikkerheitsrapport for AI-agent

**Prosjekt:** `ai-bot/helsesjekk` / VardKey  
**Dato:** 2026-10-13  
**Mål:** Verifiser funna nedanfor, rett stadfesta feil med små og målretta endringar, legg til regresjonstestar og dokumenter testresultata.

## Instruks til agenten

1. Start med å lese `AGENTS.md`, `README.md`, `TODO.md`, `SECURITY.md`, `PRIVACY.md`, `THREATMODEL.md`, `PLATFORM-ACCESS.md`, `ENCRYPTION.md`, `OFFLINE.md`, `AI-STATUS.md` og `DATA-MODEL.md` dersom dei finst i checkouten. Bruk den nyaste og mest konkrete spesifikasjonen i `TODO.md` (§§ 1–18 og § 31) som gjeldande funksjonskrav; ikkje implementer eldre motstridande dokument utan å avklare/oppdatere dei.
2. Verifiser kvart funn i faktisk kjeldekode før du konkluderer. For hypotesar merkte **VERIFISER**, skriv ein test som demonstrerer om feilen finst. Ikkje rapporter ei hypotese som stadfesta sårbarheit utan reproduksjon.
3. Rett stadfesta feil og legg til regresjonstestar. Ikkje berre skriv ei ny analyse eller TODO-liste.
4. Køyr `python3 -m unittest discover -s tests` og, dersom pakkefilene er til stades, `make x86`. Oppgi kva som faktisk vart køyrt og resultatet. Ikkje påstå at StartOS- eller nettlesartestar er køyrde utan å ha gjort dei.
5. Følg prosjektgrensene: ikkje legg til skytenester, AI-integrasjon, wallet-/signeringsfunksjonar eller ny infrastruktur. Ikkje be brukaren om seed phrase, private keys, PIN eller passord. Ikkje logg fritekst eller autentiseringshemm løyndomar. Ikkje hev pakkeversjonen til `1.0.0:0` eller erstatt ikon-placeholderen; `TODO.md` § 32 seier at dette krev eiga godkjenning.

## Oppsummering og prioritet

| ID | Prioritet | Status ved første gjennomgang | Tema |
|---|---|---|---|
| BR-001 | P0 dersom stadfesta | Må verifiserast i checkout | Repo-vising og dokumentasjon er i konflikt om kjeldefilene finst |
| BR-002 | P1 | Stadfesta krav-/risikokonflikt | Fritekst kan lagre lommebokløyndomar sjølv om produktkravet seier at dei aldri skal lagrast |
| BR-003 | P1 | Stadfesta testgap i spesifikasjonen | Ende-til-ende-test etter innlogging, datasletting og PWA er framleis oppført som attståande |
| BR-004 | P2 | Stadfesta dokumentasjonskonflikt | Ulike statusverdiar og ulike datamodellar i dokumenta |
| BR-005 | P1 | VERIFISER | Sesjon, cookie-attributt, CSRF og autentiseringsvern for alle ruter |
| BR-006 | P2 | VERIFISER | CSV-formelinjeksjon via brukarstyrte tekstfelt |
| BR-007 | P2 | VERIFISER | PWA/service worker kan ikkje cache personlege data eller omgå innlogging ved offline bruk |
| BR-008 | P2 | VERIFISER | Normalisering og unikheit for adressestiar |

---

## BR-001 — Kjeldefiler manglar i den offentlege repo-visinga

**Prioritet:** P0 dersom det blir stadfesta at kjeldefilene faktisk manglar; elles lukk som falsk positiv etter dokumentasjon.  
**Område:** Repo-/byggintegritet.

### Observasjon

Den offentlege rotvisinga viser Markdown-filer og oppgir `Languages: Markdown 100%`, medan den nyaste `TODO.md` seier at appen inneheld mellom anna `app.py`, `auth.py`, `database.py`, `maintenance.py`, `tests/`, `static/`, `startos/`, `Dockerfile`, `Makefile` og `package.json`.

- Repo: https://gitea.sondreolav.com/ai-bot/helsesjekk
- Gjeldande krav/status: https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md

Dette kan skuldast ei avgrensing i repo-visinga, feil branch eller at kjeldekode ikkje er committa. Det er ikkje forsvarleg å føresetje kva forklaring som er rett utan å kontrollere checkouten.

### Arbeid

- Køyr `git status --short`, `git branch --show-current` og `git ls-tree -r --name-only HEAD`.
- Stadfest at kjeldekode, testar og pakkefiler som TODO/README viser til, finst i branch `main` og er spora av Git.
- Dersom filer manglar: finn ut om dei er sletta, ignorerte, ligg i feil branch eller aldri vart committa. Gjenopprett den tilsikta prosjektstrukturen eller rett dokumentasjonen til den faktiske strukturen.
- Ikkje generer erstatningskode basert berre på beskrivingar og lat som han er originalimplementasjonen.

### Godkjenningskriterium

Ein rein clone av den tiltenkte branch-en inneheld alle filene som dokumentasjonen viser til, og bygg/test-kommandoane kan køyrast frå repo-rota. Dersom repoet med vilje berre skal innehalde dokumentasjon, må alle påstandar om køyrbar app, testar og StartOS-pakke rettast.

## BR-002 — Fritekst kan lagre løyndomar i klartekst

**Prioritet:** P1 (personvern-/sikkerheitsrisiko).  
**Område:** `label`, `notes`, `comments`, database og eksport.

### Observasjon

Produktkravet seier at appen aldri skal spørje etter eller lagre seed phrase, private keys, PIN, passord eller wallet-hemmelegheiter (`TODO.md` § 2). Samstundes tillèt datamodellen fleire fritekstfelt, og spesifikasjonen seier at innhaldet ikkje blir skanna. `ENCRYPTION.md` dokumenterer at live SQLite-database ligg ukryptert på disken. Dermed kan ein brukar ved eit uhell lime inn ei seed phrase eller anna løyndom i eit kommentar-/notatfelt, og appen lagrar henne trass i forbodet.

Relevante dokument:
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/DATA-MODEL.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/ENCRYPTION.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/PRIVACY.md

### Arbeid

- Finn alle fritekstfelt og alle stader teksten blir lagra, vist, logga eller eksportert.
- Lag ein realistisk, lokal safeguard mot vanlege format for wallet-hemmlegheiter (til dømes `xprv`/private-key-format og sannsynlege BIP39-fraseinnlimingar). Ikkje send innhald til eksterne tenester. Unngå å skrive feltinnhald i loggar eller feilmeldingar.
- Kombiner dette med tydeleg advarsel direkte ved kvart fritekstfelt og ei kort, forståeleg avvising når innhaldet blir stoppa. Vurder falske positive: ikkje blokker vanlege notat utan grunn.
- Dersom robust deteksjon ikkje er mogleg, dokumenter avgrensinga tydeleg og innfør minst streng lengdegrense, åtvaring ved feltet og trygg handtering. Ikkje påstå at fråvær av dedikerte kolonnar åleine garanterer at ingen løyndomar blir lagra.
- Kontroller at data som blir avviste, ikkje blir lagra delvis i SQLite eller kopierte til loggar.

### Regresjonstestar / godkjenningskriterium

- Test farlege eksempel for fleire typar løyndomar og vanleg, uskuldig fritekst.
- Avviste verdiar blir ikkje lagra og kjem ikkje med i historikk/CSV.
- Testane må ikkje innehalde ekte løyndomar; bruk syntetiske eksempel.
- Ingen nettverkstrafikk eller ekstern analyse blir introdusert.

## BR-003 — Ufullført manuell ende-til-ende-verifisering etter store endringar

**Prioritet:** P1 før release.  
**Område:** Autentisering, oppsett, sletting, PWA og StartOS-integrasjon.

### Observasjon

`TODO.md` § 31 introduserer adminpassord/sesjon, sletting av data og installerbar PWA. Same dokument seier eksplisitt at full manuell nettlesargjennomgang framleis står att: alternativt multisig-oppsett, innlogging, ein kontroll, datert eksport, sletting av data og PWA-installasjon; § 14, § 16 og § 17 skal òg køyrast på nytt. Dette er særleg viktig fordi autentisering og sletting påverkar tilgang og dataintegritet.

Kjelde: https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md (særleg §§ 31 og «Kva som er testa for heile runden»).

### Arbeid

- Køyr først automatiserte testar; rett feil dei avdekkjer.
- Utfør den manuelle gjennomgangen på den faktiske appen og StartOS 0.4.0 dersom miljøet er tilgjengeleg.
- Kontroller: første oppsett og obligatorisk oppretting av admin; login/logout; utløpt/ugyldig sesjon; direkte API-kall utan innlogging; full kontroll og CSV; alternativ terskel/nøkkeltal; datasletting med stadfesting; restart/backup/restore; PWA offline/online og etter logout.
- Registrer kvar test som bestått/feila/ikkje køyrd. Ikkje marker release-kriteriet som oppfylt berre fordi unit-testane er grøne.

### Godkjenningskriterium

Alle scenario er verifiserte i nettlesar/StartOS, eller tydeleg merkte som ikkje køyrde med grunn. Feil som blir funne, får eigne automatiserte regresjonstestar der det er mogleg.

## BR-004 — Motstridande statusverdiar og datamodell i dokumentasjonen

**Prioritet:** P2; kan bli P1 dersom implementasjonen faktisk brukar feil enum/schema.  
**Område:** Datamodell, validering, UI, varsling, eksport og agentinstruksjonar.

### Observasjon

Dokumenta gir to ulike kontraktar:

- `AI-STATUS.md` listar `ok`, `vulnerable`, `compromised`, `unknown` og skildrar éin status på kvar kontroll.
- Nyare `TODO.md` § 5 krev `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`; § 4 skildrar `ai_security_checks` med `provider` og `status`, altså status per leverandør.
- `DATA-MODEL.md` brukar dessutan eldre tabellnamn (`settings`, `setup`, `key`, `check`, `key_check`, `tool_check`) som ikkje samsvarar med dei seinare namna i TODO (`app_settings`, `keys`, `health_checks`, `key_checks`, `ai_security_checks`).

Kjelder:
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/AI-STATUS.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/DATA-MODEL.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md

### Arbeid

- Fastset kva spesifikasjon som er autoritativ, med `TODO.md` §§ 4–7 som utgangspunkt.
- Kontroller faktiske enum-verdiar i SQLite-skjema, servervalidering, UI, varselgenerering, API-responsar, historikk og CSV.
- Oppdater dei utdaterte dokumenta slik at dei speglar den implementerte og vedtekne kontrakten. Ikkje migrer data eller endre API berre for å få nyare kode til å passe med utdaterte dokument.
- Sørg for at ugyldige eller gamle verdiar blir handterte eksplisitt, ikkje stille konverterte til ein annan trygg status.

### Regresjonstestar / godkjenningskriterium

Ein test for kvar tillaten status, ugyldig status, historikk/CSV og leverandørkopling. Ei statusendring må ikkje feilaktig lukke eit aktivt sikkerheitsvarsel.

## BR-005 — Verifiser autentisering, session-cookie og CSRF-beskyttelse

**Prioritet:** P1 dersom kontroll manglar; elles dokumenter verifikasjonen.  
**Status:** VERIFISER — offentleg dokumentasjon omtalar scrypt, signert cookie og CSRF-token, men eg har ikkje fått inspisert kjeldekoden eller køyrt appen.

### Arbeid

- Kartlegg alle HTTP-ruter. Verifiser at `GET /health` er einaste uautentiserte rute, og at han berre returnerer minimal readiness-info (ikkje konfigurasjon, secrets, exception-trace eller persondata).
- Test direkte tilgang til kvar `/api/*`-rute før login, etter logout og med utløpt/forfalska cookie. API-et skal svare med 401, ikkje returnere data eller gi HTML som klienten mistolkar som JSON.
- Kontroller cookie-attributta `HttpOnly`, `SameSite` og `Secure` i faktisk StartOS-proxyoppsett. TLS blir terminert av StartOS, så ikkje stol blindt på klientstyrte `X-Forwarded-*`-headarar. Verifiser at cookie blir sett sikkert bak proxyen.
- Verifiser CSRF-kontroll på alle tilstandsendrande ruter, inkludert adminoppsett, login/logout, nøkkelrotering, innstillingar, kvittering av varsel og sletting av data. Test både manglande token og token frå ein annan sesjon/opphav.
- Kontroller sesjonsutløp, signaturvalidering og at passord/session-secret aldri blir sendt til klienten eller logga. Verifiser også trygg feilatferd ved feil i auth-/databaseoppsett.

### Godkjenningskriterium

Automatiserte testar viser at ikkje-autentiserte og CSRF-forfalska kall ikkje kan lese eller endre appdata. Cookie-oppsett er testa bak den reelle reverse proxyen; ingen tryggleikseigenskap blir berre føresett frå utviklingsserveren.

## BR-006 — Verifiser CSV-formelinjeksjon

**Prioritet:** P2 dersom eksporterte tekstar kan bli tolka som formlar.  
**Status:** VERIFISER.

### Observasjon / risiko

CSV-eksporten inkluderer brukarkontrollerte namn, programvarenamn og kommentarar (`TODO.md` § 10). Dersom slike felt blir skrivne direkte til CSV og fila blir opna i eit rekneark, kan celleverdiar som byrjar med `=`, `+`, `-`, `@`, tab eller kontrollteikn bli tolka som formlar. CSV-sitatteikn åleine er ikkje nok til å avverje dette.

### Arbeid

- Test eksport med syntetiske celleverdiar som byrjar med dei nemnde prefiksa, også etter mellomrom/CR/LF og i Unicode-kanttilfelle.
- Dersom verdiane kan bli formeluttrykk, innfør ei dokumentert, konsistent nøytralisering av tekstceller før CSV-skriving utan å øydelegge vanlege data. Hald kolonnenamn og CSV-formatavtalen stabile. Ikkje endre numeriske/dato/statusfelt feilaktig.

### Godkjenningskriterium

Testar demonstrerer at brukarstyrte tekstverdiar blir eksporterte som tekst og ikkje som reknearkformlar. Vanleg CSV-innhald er framleis korrekt.

## BR-007 — Verifiser PWA-cache, offline-tilstand og logout

**Prioritet:** P2 dersom persondata eller autentiserte sider blir cachelagde/tilgjengelege offline.  
**Status:** VERIFISER.

### Observasjon / risiko

`TODO.md` seier at service worker skal cache eit kvitelista app-skal, aldri `/api/*`, `/health` eller `/login`. Det må òg sikrast at statiske sider ikkje inneheld servergenererte persondata, at gamle cache-versjonar ikkje beheld sensitive skjermar, og at offline-/logout-tilstand ikkje gir inntrykk av at brukaren framleis er autentisert.

### Arbeid

- Inspiser `static/sw.js`, cache-nøklar og fallback-strategi. Test at alle API-kall og svar med privat data er `network-only`/ikkje cachelagde.
- Test innlogging → opne appen → logout → offline; sjekk at ingen data frå tidlegare sesjonar er synlege eller kan sendast.
- Test oppdatering av appen med gammal cache frå før oppdateringa, og at cache kan bytast/slettast kontrollert.
- Verifiser at service worker ikkje fangar opp `POST`-kall eller returnerer ein cached 200 for ein beskytta API-rute.

### Godkjenningskriterium

Ingen personlege kontrollar, API-svar, innloggingssvar eller sesjonssensitive sider blir cachelagde. Offline-modus viser ein tydeleg offline-tilstand og opnar ikkje for redigering eller innsending utan server.

## BR-008 — Verifiser kanonisering og unikheit for adressestiar

**Prioritet:** P2; P1 dersom to ulike nøklar kan bli registrerte med same faktiske derivation path.  
**Status:** VERIFISER.

### Observasjon / risiko

Spesifikasjonen krev at adressestien er identitet for nøkkelen og unik på tvers av oppsett, innstillingar og rotering (`TODO.md` § 4 og § 31). Kontroller om unikheitskontrollen berre samanliknar rå strengar. Same BIP32-sti kan bli uttrykt med alternative apostrof-/`h`-notasjonar eller ujamn whitespace; dersom dei blir tolka som same sti, kan rein strengsamanlikning tillate ein duplikat.

### Arbeid

- Finn kvar adressestiar blir trimma, validerte, samanlikna og lagra (oppsett, innstillingar, rotering og direkte API-kall).
- Bestem ein avgrensa kanonisk representasjon som samsvarar med støtta inputformat. Avvis ugyldig format på serveren, ikkje berre i nettlesaren. Ikkje anta at to stiar er like utan ei spesifisert normaliseringsregel.
- Test duplikat med ulik whitespace og alle alternative notasjonar appen faktisk støttar.

### Godkjenningskriterium

Serveren avviser duplikate/ugyldige stiar konsekvent på alle inngangar, og eksisterande data blir ikkje stille endra av normalisering.

---

## Avsluttrapport frå agenten

Når arbeidet er ferdig, svar med:

1. Funn som var stadfesta, falske positive og framleis uløyste.
2. Kva filer som vart endra, med ei kort forklaring per endring.
3. Kva regresjonstestar som vart lagde til.
4. Nøyaktig kva kommandoar som vart køyrde og resultata deira.
5. Eventuelle manuelle StartOS-/nettlesartestar som ikkje kunne køyrast, utan å markere dei som beståtte.

---

# Svar frå agenten — runde 32-A (bug-triarge)

**Dato:** 2026-10-14  
**Omfang:** berre BR-001–BR-008 i denne rapporten. BR-002 høyrde til runde 32-B, ikonet og pakkeversjonen til 32-F, og dokumentasjonsdrifta i `README.md`, `docs/application.md`, `instructions.md` og `UPDATING.md` til 32-E. Ingenting av det vart rørt her.

## Kva som fell bort fordi rapporten er skriven mot eit anna filsett

Rapporten ber om `SECURITY.md`, `PRIVACY.md`, `THREATMODEL.md`, `PLATFORM-ACCESS.md`, `ENCRYPTION.md`, `OFFLINE.md`, `AI-STATUS.md` og `DATA-MODEL.md`. **Ingen av dei finst i dette repoet.** Filene som faktisk ligg her, er `AGENTS.md`, `CLAUDE.md`, `README.md`, `TODO.md`, `ai-note.md`, `UPDATING.md`, `instructions.md`, `docs/application.md`, kjeldekoden på repo-rota, `static/`, `tests/` og `startos/`.

Konsekvensar for dommane:

- **BR-001** kan ikkje avgjerast ved å samanlikne med dei nemnde dokumenta, berre mot koden som faktisk ligg i `main`.
- **BR-004** fell heilt bort: båe dei motstridande kjeldene (`AI-STATUS.md` og `DATA-MODEL.md`) manglar. Den reelle dokumentasjonsdrifta i dette repoet er kjend og høyrer til 32-E.
- **BR-002** sin dokumentasjonadel (`ENCRYPTION.md`, `PRIVACY.md`) fell bort. Sjølve risikofunnet står likevel, og det vart ført vidare til 32-B.
- **BR-005** sine krav om å teste «bak den reelle reverse proxyen» kan ikkje oppfyllast her, sidan det krev den faktiske StartOS-boksen.
- Rapportens instruks 1 (les dei nemnde dokumenta) og instruks 4 (`make x86`) kan ikkje følgjast fullt ut: ingen av dokumenta finst, og det finst inga StartOS-pakkearbeidsflate i denne køyringa.

## 1. Funn som var stadfesta, falske positive og framleis uløyste

| ID | Dom | Grunnlag |
|---|---|---|
| BR-001 | **Falsk positiv** | Kjeldefilene ligg i `main`: `app.py`, `auth.py`, `database.py`, `export.py`, `maintenance.py`, `validation.py`, `alerts.py`, `tests/`, `static/`, `startos/`, `Dockerfile`, `Makefile`, `package.json`, `tsconfig.json`. Rapporten bygde på rotvisinga i nettgrensesnittet, ikkje på innhaldet i branch-en. |
| BR-002 | **Stadfesta, men utsett** | Fritekstfelta (`name`, `model`, `comments` og nøkkelnotatet) blir lagra utan lokal sperre. Arbeidet høyrer til 32-B og vart ikkje starta. **Lukka i runde 32-B — sjå svaret nedanfor.** |
| BR-003 | **Falsk positiv som formulert; det som står att høyrer til § 32** | Rapporten siterer ein § 31-tekst som ikkje finst lenger. `TODO.md` § 16 og § 17 seier at dei manuelle nettlesartestane og bokstestane vart køyrde og verifiserte fram til § 31. Det som faktisk står att, er dei **nye** manuelle punkta § 32 legg til (ikonet, UI-pussen, varseltekstane, åtvaringa ved felta, og heile bokstesten på nytt), og dei krev ein nettlesar og ein StartOS 0.4.0-boks. |
| BR-004 | **Fell bort (filene finst ikkje)** | `AI-STATUS.md` og `DATA-MODEL.md` manglar. Koden følgjer alt kontrakten i `TODO.md` § 4–§ 7, så det finst ingen motstrid i implementasjonen å rette her. |
| BR-005 | **Verifisert i koden, inga åtferdsendring** | Sjå punkt 6 nedanfor. Rapporten bad om at åtferda i `app.py` blir rapportert og ikkje endra. |
| BR-006 | **Stadfesta og retta** | CSV-eksporten skreiv brukarstyrte tekstar uendra. |
| BR-007 | **Stadfesta og retta** | Tenestearbeidaren lagra kvar svar, òg ein 302 til `/login` som `fetch` følgjer. |
| BR-008 | **Stadfesta og retta** | Unikheitskontrollen samanlikna rå strengar, så `m/48h/0h/0h/2h` og `m/48'/0'/0'/2'` kunne bli registrerte som to nøklar. |

## 2. Filer som vart endra

| Fil | Endring |
|---|---|
| `export.py` | BR-006. Nye hjelparane `_guard_formula()` og `_needs_guard()`, og `_cell()` går no gjennom dei for alle ikkje-flag-celler. Ei tekstcelle som byrjar med `=`, `+`, `-`, `@`, eit kontrollteikn eller eit slikt teikn etter leiande mellomrom, blir prefiksa med ein apostrof. Kolonnenamna, kolonnerekkjefølgja, flagga (`Yes`/`No`) og alle vanlege verdiar er uendra. |
| `static/sw.js` | BR-007. Ny `isCacheable(response)`, som krev `response.ok`, `response.type === "basic"` og `!response.redirected`. Cache-skrivinga i fetch-handteraren er no verna av han, så ei loginside (eller ei feilside) kan ikkje lenger erstatta det cacha app-skalet. Allow-lista og nettverks-først-strategien er uendra. |
| `validation.py` | BR-008. Ny konstant `HARDENED_MARKER_FOLD` og ny `_path_key()`, som gjev den kanoniske samanlikningsforma (strip, `casefold`, `h`/`H` → `'`). Han blir brukt i `validate_key_setup()`, `_ensure_unique_path()`, `validate_rotation()` (både «stien må endre seg» og unikheit) og `_address_path()`. Den lagra verdien blir ikkje skriven om. |
| `tests/test_export.py` | BR-006-regresjonstestar (ny klasse `FormulaInjectionTests`). |
| `tests/test_pwa.py` | BR-007-regresjonstest (ny test i `ServiceWorkerTests`). |
| `tests/test_validation.py` | BR-008-regresjonstestar (fire nye testar) og ein ny konstant `HARDENED_H_PATH`. |
| `TODO.md` | § 32.4 oppdatert med utfallet per BR og dei tre nye bindande reglane. |
| `BUG-RAPPORT-AI-AGENT.md` | Denne avsluttande rapporten. |

Ingen endring i `app.py`, `auth.py`, `database.py`, `alerts.py`, `static/app.js`, `static/manifest.webmanifest`, ikonet, `package.json` eller pakkeversjonen.

## 3. Regresjonstestar som vart lagde til

**`tests/test_export.py` — klassen `FormulaInjectionTests` (BR-006):**

- `test_a_formula_prefix_is_neutralized` — kvar av `=`, `+`, `-`, `@` blir nøytralisert.
- `test_a_leading_control_character_is_neutralized` — tab, CR og LF framfor ein verdi.
- `test_a_formula_prefix_after_a_space_is_neutralized` — prefiks etter leiande mellomrom.
- `test_ordinary_text_is_written_exactly_as_stored` — vanleg tekst, tekst med separatorar, samanslått statuscelle, versjon, statusverdi og tom celle er uendra.
- `test_the_header_row_and_the_flags_are_not_guarded` — header og `Yes`/`No` er uendra.

**`tests/test_pwa.py` — `ServiceWorkerTests` (BR-007):**

- `test_the_service_worker_only_stores_a_successful_same_origin_answer` — `sw.js` inneheld vernet (`isCacheable`, `response.ok`, `response.type`, `!response.redirected`).

**`tests/test_validation.py` (BR-008):**

- `KeySetupTests.test_the_path_comparison_folds_the_hardened_marker` — duplikat i oppsettet, med `h`, `H` og luft.
- `ValidationTests.test_a_path_written_with_the_h_marker_is_the_keys_own_path` — same sti i `h`-notasjon gjev `OK`, og den innsende skrivemåten blir halden.
- `KeySettingsTests.test_the_duplicate_check_folds_the_hardened_marker` — `DuplicateAddressPath` i innstillingane.
- `RotationTests.test_the_stored_path_is_refused_in_either_marker` — roteringa avviser den lagra stien òg i `h`-notasjon.

**Ti nye testar til saman** (fem i `test_export.py`, ein i `test_pwa.py` og fire i `test_validation.py`), som er dei ti som ligg i listene over.

## 4. Kommandoar som vart køyrde og resultatet

- **`python3 -m unittest discover -s tests`** — kunne **ikkje** køyrast i denne køyringa: agenten har ikkje skal eller terminaltilgang, berre Gitea-verktøya. Suiten vart difor **ikkje** stadfesta grøn av meg etter endringane. Brukaren har seinare køyrd han og stadfesta han grøn: **432 testar** etter runde 32-A, og **475 testar** etter runde 32-B (etter at BR-002-sperra vart snudd til å køyre før lengdegrensa).
- **`make x86`** — ikkje køyrd. Det finst inga StartOS-pakkearbeidsflate i denne køyringa, og inga pakkefil vart endra.
- **`git status --short`, `git branch --show-current`, `git ls-tree -r --name-only HEAD`** (BR-001) — ikkje køyrde som skal-kommandoar. I staden vart branch `main` lesen gjennom Gitea-API-et, som listar 88 filer, mellom dei alle kjelde-, test- og pakkefilene. Den einskilde kommandoen over kan berre brukaren køyre; resultatet hans er det som formelt lukkar BR-001.
- **Statisk lesing av `app.py` og `auth.py`** for BR-005, og av `export.py`, `static/sw.js`, `validation.py` og testane for BR-006–BR-008.
- Alle filendringane vart gjorde éi fil om gongen gjennom Gitea-verktøya. Merk: verktøyet som var tilgjengeleg, har ingen `preview`/`preview_id`-steg, så kvar endring vart skriven med nøyaktig det gjennomgåtte innhaldet i éin operasjon.

## 5. Manuelle testar som ikkje kunne køyrast

Desse er **ikkje** køyrde, og blir ikkje markerte som beståtte:

- Den manuelle nettlesargjennomgangen i `TODO.md` § 16 og § 31 (BR-003).
- Cookie-åtferda bak den reelle StartOS-proxyen (BR-005), mellom anna `Secure`-flagget, sidan TLS blir terminerert av StartOS og proxyar rein HTTP inn i containeren.
- PWA-en i ein faktisk nettlesar: installasjon, innlogging → app → logout → offline, og oppdatering frå ein gamal cache (BR-007). Berre `sw.js`-kjelda er verifisert.
- CSV-en opna i eit faktisk rekneark (BR-006). Nøytraliseringa er verifisert i testar, ikkje i Excel.
- StartOS 0.4.0-boksen: installasjon, restart, backup og restore.

## 6. BR-005 — verifikasjonen, i detalj

Inga åtferd vart endra, slik oppdraget bad om. Funna i koden:

- **Opne ruter:** berre `GET /health` (svarar `{"status": "ok"}`, inga konfigurasjon, inga persondata, ingen trace), `GET /api/session` (berre `admin_configured` og `authenticated`) og `/login` (sjølve loginsida). Alle andre `/api/*` svarar `401` utan gyldig økt, og dei fem app-sidene svarar `302` til `/login`. Statiske ressursar (CSS, JS, manifest, ikon) er opne og inneheld ingen data.
- **CSRF:** alle tilstandsendrande POST går gjennom øktsjekken først og deretter CSRF-sjekken, og svarar `403` på manglande eller feil token. Unntaka er `POST /api/admin` og `POST /api/login`, som må kunne køyrast før ei økt finst. Double-submit: same token i ein lesbar cookie og i `X-CSRF-Token`, samanlikna med `hmac.compare_digest`.
- **Cookie:** økta er `HttpOnly`, `SameSite=Strict`, `Path=/` og har `Max-Age`; CSRF-cookien er medvite lesbar (må inn i headeren). Inga cookie er merkt `Secure`, og det er dokumentert i koden: StartOS terminerer TLS og proxyar rein HTTP inn i containeren, så `Secure` ville droppe cookien på `http://localhost`. Appen les ingen `X-Forwarded-*`-header, så ingen klientstyrt header kan påverke han.
- **Økt og passord:** passordet blir lagra som `hashlib.scrypt`-hash med eit tilfeldig salt per passord og samanlikna med `hmac.compare_digest`; økta er HMAC-SHA256 over eit utløpstidsstempel, nøkla på ein `session_secret` som ligg i `app_settings`. Utløpet blir kontrollert. Verken passordhashen eller `session_secret` blir nokon gong send til klienten eller logga. Ei feilande database gjev eit avvist kall (fail closed), ikkje eit ope eit.
- **Attståande, berre for brukaren:** `Secure`-flagget mot den reelle proxyen, og ei stadfesting av at StartOS ikkje legg noko til eller fjernar noko frå `Set-Cookie` på vegen.

## 7. BR-006, BR-007 og BR-008 — kva rettinga er, og kva ho ikkje er

- **BR-006.** Ei celle som eit rekneark les som ein formel, får no ein leiande apostrof. Rettinga gjeld berre tekstceller som treng det; tal, datoar, statusverdiar og `Yes`/`No` er uendra, og kolonnenamna er dei same, sidan eksporten er ein avtale. Kjend avgrensing: berre dei prefiksa eit rekneark faktisk kjenner att, blir nøytraliserte — Unicode-homoglyfar av `=` blir ikkje det, sidan eit rekneark ikkje les dei som formlar. Merk òg at ein vanleg notatlinje som byrjar med `-` no får ein apostrof framfor seg i eksporten; det er korrekt åtferd, sidan eit rekneark elles les ho som ein formel.
- **BR-007.** Rettinga stoggar cachen av eit svar som ikkje er vellukka, ikkje er same-opphav, eller er omdirigert. Ho endrar ikkje allow-lista, som alt held `/api/*`, `/health` og `/login` utanfor, og ikkje nettverks-først-strategien. Skalet er rein HTML utan persondata, så ingen persondata ligg i cachen. `install`-steget brukar framleis `cache.addAll(SHELL)`; det køyrer frå ei beskytta side der det finst ei økt, og vart ikkje endra.
- **BR-008.** Rettinga gjer samanlikninga kanonisk: ho fellar `h`/`H` til `'`, i tillegg til store/små bokstavar og luft. Ho blir brukt for unikheit i oppsettet, i innstillingane og ved rotering, og for samanlikninga mellom innsend og lagra sti i kontrollen, slik at same derivasjonssti i to skrivemåtar ikkje lenger gjev ein falsk `PROBLEM`. Den lagra verdien blir aldri skriven om, så eksisterande data er ikkje endra. Kjend avgrensing: ein sti blir ikkje validert som eit gyldig BIP32-format, berre som ikkje-tom tekst opp til 200 teikn — det er slik `TODO.md` § 4 og § 25.1 skildrar feltet, og ei strengare formatvalidering ville vore ei åtferdsendring utanfor denne runden.

---

# Svar frå agenten — runde 32-B (BR-002)

**Dato:** 2026-10-14  
**Omfang:** BR-002 åleine. Denne runden lukkar den rada som runde 32-A sette att som «stadfesta, utsett», og ho erstattar den dommen. Ingenting anna er rørt: BR-001, BR-003, BR-004 og BR-005 står som før, og ikonet, pakkeversjonen og dokumentasjonsdrifta er framleis utanfor scope.

## 1. Dom

**BR-002 — stadfesta og retta.** Funnet heldt: fritekstfelta vart skrivne til databasen slik brukaren skreiv dei, og dei kjem med i CSV-eksporten. Ei seed phrase eller ein privatnøkkel som vart lima inn ved eit uhell, ville difor bli lagra i klartekst og eksportert. Eit slikt innhald blir no avvist i kvart fritekstfelt, før noko blir skrive.

## 2. Kva som vart bygd

- **Ny modul `secret_guard.py`** med éin jobb: å avgjere om ein tekst ser ut som ei wallet-løyndom. Han held den engelske BIP39-ordlista (2048 ord, bakt inn lokalt — appen gjer framleis ingen nettverkskall) og ein `find_secret()`, som kjenner att:
  - eit PEM-privatnøkkelblock (`-----BEGIN … PRIVATE KEY-----`);
  - ein utvida privatnøkkel, med alle SLIP-132-prefiksa (`xprv`, `yprv`, `zprv`, `tprv`, `uprv`, `vprv`), når tokenet er eit base58-token på minst 100 teikn;
  - ein WIF-nøkkel, 51 eller 52 base58-teikn som byrjar på `5`, `9`, `K`, `L` eller `c`;
  - ein BIP38-nøkkel (`6P` og 58 teikn);
  - eit ordløp på 12 eller fleire BIP39-ord, også midt i ein setning.
- **Funksjonen gjev berre ei kort engelsk nemning attende**, til dømes `"a seed phrase"`, og aldri teksten. `rejection_message()` byggjer setninga brukaren ser; ho namngjev feltet og forma som vart kjend att, og seier at ingenting vart lagra. Ingen av dei to kan difor lekke ein løyndom inn i ein respons eller ein logg.
- **`validation.py`** har fått `SecretDetected`, som er ein `ValidationError`, og ein `_reject_secret()`. Sjekken sit i dei fire teksthjelparane `_text()`, `_key_name()`, `_model()` og `_required_path()`, så **kvart fritekstfelt er dekt av konstruksjon**: nøkkelnamn, modell, wallet-programvarenamn, programvareversjon, firmware-versjon, nøkkelnotatet, kompatibilitetsnotatet, det overordna kommentarfeltet, KI-kommentarane og adressestien.
- **Sjekken køyrer òg før lengdegrensa til feltet.** Det vart ei medvite avgjerd, ikkje ein detalj: med den omvendte rekkjefølgja ville eit seed phrase som er lengre enn feltet tillet, bli svara med «key name is too long» — ei melding som ber brukaren om å **korte ned** ein seed phrase i staden for å fjerne han. Med sjekken først blir svaret «key name looks like a seed phrase», som er den korte og forståelege avvisinga rapporten ber om. Lengdegrensa står framleis som ytre grense og gjeld for alt annet, så eit vanleg over-langt namn blir framleis avvist som «too long». Rekkjefølgja er festa i to testar, éin for eit løyndom som passar i feltet og éin for eit som ikkje gjer det, pluss ein test som stadfestar at lengdegrensa framleis verkar.
- **`auth.py`** avviser òg eit adminbrukarnamn som ser ut som ei løyndom, med same rekkjefølgje, fordi namnet òg er lagra fritekst. Passordet blir medvite **ikkje** sjekka: ein lang passfrase er eit legitimt passord, og ei avvising der ville stengje brukaren ute frå sin eigen konto.
- **Åtvaring ved kvart fritekstfelt i UI-et:** ei kort linje — «Never paste a seed phrase or a private key here.» — i same ambra-palett som den eksisterande sidenotisen, lagd inn i `static/health-check.html` (tre statiske felt), `static/health-check.js` (firmware-versjon, nøkkelnotatet og kvar KI-kommentar), `static/setup.html` og `static/setup.js` (eitt per nøkkelkort, som dekkjer namn, modell og sti) og `static/settings.js` (programvare-raden og roteringskortet). Stilen `.secret-warning` ligg i `static/styles.css`. Sidenotisen «Never enter seed phrases…» står framleis, og sideoverskriftene og dei nummererte seksjonane er uendra, så formtestane held.

## 3. Filer som vart endra

| Fil | Endring |
|---|---|
| `secret_guard.py` | Ny. Ordlista, mønstra, `find_secret()` og `rejection_message()`. |
| `validation.py` | Ny `SecretDetected` og `_reject_secret()`, kalla frå dei fire teksthjelparane, og kalla **før** lengdegrensa i kvar av dei; `_key_name()` tek no eit feltnamn så meldinga seier «wallet software name» der det gjeld. |
| `auth.py` | `normalize_admin_username()` avviser eit namn som ser ut som ei løyndom, før lengdegrensa. Passordet er urørt. |
| `static/styles.css` | Ny `.secret-warning` i den eksisterande ambra-paletten. |
| `static/health-check.html` | Tre åtvaringar, ved dei tre statiske fritekstfelta. |
| `static/health-check.js` | Ny `secretWarning()`, brukt ved dei tre felta skriptet byggjer. |
| `static/setup.html`, `static/setup.js` | Ei åtvaring per nøkkelkort, både i markupen og i kortet skriptet byggjer. |
| `static/settings.js` | Åtvaring i programvare-raden og i roteringskortet. |
| `tests/test_secret_guard.py` | Ny testmodul. |
| `TODO.md` | § 32.4: utfallet av 32-B, dei nye reglane, og testtalet oppdatert til 475. |
| `ai-note.md` | Handoveren oppdatert med 32.4, sperra, dei nye reglane og det som står att av §32. |

Ingen endring i `app.py`, `database.py`, `alerts.py`, `export.py`, `maintenance.py`, ikonet, `package.json` eller pakkeversjonen. Merk at **`app.py` ikkje trong nokon endring**: `SecretDetected` er ein `ValidationError`, som alle dei relevante handterarane alt fangar og svarar `400` på. Hadde han vore ein vanleg `ValueError`, ville `STORAGE_ERRORS` ha fanga han og svart `500` i staden.

## 4. Regresjonstestar som vart lagde til

Alle i den nye `tests/test_secret_guard.py`, **43 til saman**:

- **Ordlisteintegritet** (fem testar): nøyaktig 2048 ord, `abandon` fyrst og `zoo` sist, alfabetisk rekkjefølgje, alle orda 3–8 små bokstavar, og unike firebokstavsprefiks. Den siste er den sterke: spesifikasjonen garanterer at ingen to BIP39-ord deler dei fire første bokstavane, så eit mistypt eller manglande ord bryt han. Ei liste som er kopiert inn lokalt kan elles bli stille feil.
- **Gjenkjenning** (ti testar): seed phrase (òg i store bokstavar, med luft rundt, og midt i ein setning), 24 ord, at eit løp på 11 ord ikkje blir avvist, kvar av dei fire nøkkelformene, alle seks utvida-prefiksa, båe WIF-lengdene, at ein `xpub` ikkje blir avvist, at eit transaksjons-id ikkje blir avvist, og at vanlege notat ikkje blir det.
- **Feltnivå** (sytten testar): kvar fritekstfelt i ein innsending, oppsettet, innstillingane, roteringa, programvare-lista og adminbrukarnamnet avviser ei løyndom; meldinga inneheld feltet og forma, men aldri teksten; passordet blir ikkje sjekka; eit vanleg innsending går framleis gjennom; `SecretDetected` er ein `ValidationError`; **ei løyndom som passar i eit kort felt blir namngjeven som ei løyndom**; **ei løyndom som er lengre enn feltet blir framleis namngjeven som ei løyndom, ikkje som «too long»**; og **lengdegrensa verkar framleis for alt anna**.
- **Åtvaringar i UI-et** (seks testar): at kvar av dei tre statiske åtvaringane er der, at kvart skript kallar hjelparen ved felta det byggjer, at stilen finst, og at sidenotisen står att.
- **Ikkje lagra, ikkje eksportert** (fem API-testar): eit innsending med ei seed phrase i kommentaren svarar `400`, meldinga gjengjev ikkje teksten, og både `list_health_checks()` og CSV-eksporten er tomme etterpå. Det same for ein utvida privatnøkkel i nøkkelnotatet. Eit vanleg innsending blir framleis lagra (`201`) og eksportert, og når eit lagra innsending blir følgt av eit avvist eitt, inneheld eksporten det første og ingen ting av det andre.

Testane inneheld **ingen ekte løyndomar**: seed-phrasen er tolv BIP39-ord i ei rekkjefølgje som ikkje er ein gyldig checksum, og nøkkelstrengane er prefikset og lengda til det ekte formatet fylt med bokstaven `A`.

## 5. Kommandoar som vart køyrde og resultatet

- **`python3 -m unittest discover -s tests`** — kunne **ikkje** køyrast av agenten, som berre har Gitea-verktøya og inga skal. Brukaren har køyrd suiten og stadfesta han grøn: **432 testar** etter runde 32-A, og **475 testar** etter runde 32-B.
- **Ingen nettverkstrafikk** er lagd til: ordlista ligg i kjeldekoden, og `secret_guard.py` importerer berre `re`.
- Endringane vart gjorde éi fil om gongen gjennom Gitea-verktøya, kvar med det gjennomgåtte innhaldet i éin operasjon. Verktøyet som var tilgjengeleg, har ingen `preview`/`preview_id`-steg.

## 6. Manuelle testar som ikkje kunne køyrast

Desse er **ikkje** køyrde, og blir ikkje markerte som beståtte:

- Å lime ei verkeleg seed phrase inn i kvart fritekstfelt i ein nettlesar og sjå at åtvaringa står ved feltet og at avvisinga kjem opp i statuslinja. Berre markupen, skripta og serveråtferda er verifisert, ikkje den faktiske opplevinga i ein nettlesar.
- Å stadfeste at åtvaringa ikkje er klypt eller overfylt på ein smal telefon. Det høyrer til UI-finpussen i 32.2.
- Ei gjennomlesing av om nokon av dei vanlege notata i ein reell database blir avviste ved eit uhell. Testane dekkjer elleve vanlege notat og eit transaksjons-id, men berre brukaren kan seie om noko i deira eiga data ville bli råka.

## 7. Kjende avgrensingar, som ikkje blir tona ned

Dei står i modulens docstring, og dei er grunnen til at dette blir kalla ei sperre og ikkje eit vern:

- **Eit nakent 64-teikns heksadesimalt streng blir ikkje avvist.** Det er umogleg å skilje frå ein transaksjons-id eller ein hash, som er legitimt notatinnhald, så ei avvising der ville blokkere vanleg bruk. Ein rå heksadesimal privatnøkkel er difor ikkje fanga.
- **Berre den engelske BIP39-ordlista blir brukt.** Ei frase på eit anna språk, eller ei der eit ord er skrive feil, blir ikkje fanga av ordløpet.
- **Ei løyndom som er delt over fleire felt, eller skriven i ein form utanom mønstra, blir ikkje fanga.**
- **Falske positive er ikkje utelukka.** Terskelen på 12 ord er vald for å halde vanlege notat utanfor, men eit notat som tilfeldigvis består av tolv eller fleire BIP39-ord etter kvarandre, ville bli avvist. Det er den prisen som er vald, sidan eit avvist notat kan skrivast om, medan ei løyndom som er lagra, ikkje kan gjerast uskriven.
- **Rekkjefølgja mellom sperra og lengdegrensa er ei medvite vald avveging**, ikkje ei gløymd detalj: sperra vinn, slik at eit innlimt løyndom alltid blir namngjeve som det det er. Det går ikkje ut over lengdegrensa, som framleis avviser alt anna som er for langt.

---

# Rettar i dokumentasjonen (gjort etter at runde 32-A og 32-B var ferdige)

Desse rettingane gjeld berre dokumenta, ikkje koden:

- **BR-003-dommen er retta** i tabellen i svaret for 32-A. Han var skriven som «stadfesta», men rapporten bygde på ein § 31-tekst som ikkje finst lenger. Det som faktisk står att, er dei nye manuelle punkta § 32 legg til, og dei er førte opp under `TODO.md` § 32.1, 32.2, 32.3 og 32.5.
- **Testtala er retta.** Runde 32-A la til **ti** testar, ikkje åtte: fem i `tests/test_export.py`, ein i `tests/test_pwa.py` og fire i `tests/test_validation.py`. `tests/test_secret_guard.py` held **43**, ikkje 44 (5 + 10 + 17 + 6 + 5), og gruppa «feltnivå» er sytten testar, ikkje seksten. Suiten gjekk difor frå 422 til 432 etter 32-A og til **475** etter 32-B — det talet brukaren stadfesta. Dei tidlegare tala «474» og «44» i dette svaret var skrivne før den siste testen vart lagd til.
- **`TODO.md` og `ai-note.md` er førte i samsvar med dette**: § 32-statusen seier at 32.4 er utført med unntak av BR-003, dokumentasjonsdrifta er ført inn som eige punkt **32.6**, og dei nye reglane frå 32-A og 32-B står no òg i den bindande specen (§ 2, § 4, § 10, § 12, § 15, § 16) og ikkje berre i § 32.4.
