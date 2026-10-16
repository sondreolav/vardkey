The user wants:

    Remove p#workflow-note (the whole element).
    Move Download CSV to after the "All checks / Saved health checks" section — i.e. give it its own section block with an h2 (title bar) and an info text, in the style of the other section blocks on the history page.

"Kan du legge "Download CSV" etter "ALL CHECKS Saved health checks", med eigen passande "h2"-del og info teskt (viss du sjønnar kva eg meinar)."

So: after the section.section-block that holds the saved-checks list (eyebrow "All checks", h2 "Saved health checks"), add a new section.section-block with an eyebrow + h2 (a title bar) + a short info text + the Download CSV link.

Design decision: what eyebrow/h2/text? Following the page's pattern:

    section.section-block with .section-heading containing <p class="eyebrow">…</p> and <h2 id="…">…</h2>, then the button and the info text.

Hmm — but note tests/test_health_check_form.py::test_the_history_page_offers_the_export_and_the_note asserts the note under the link and .page-heading > .secondary-button. If I move the link out of .page-heading, that CSS rule becomes dead, and the test's assertions about .page-heading > .secondary-button need updating.

Also: does any test assert the eyebrows on history.html exactly? test_the_form_sections_follow_the_agreed_order is for health-check.html. test_the_settings_page_has_the_two_sections is for settings.html. There's no exact-eyebrow assertion for history.html. Good. But test_app.py::test_history_page_is_served_in_english asserts id="history-list" and "Saved health checks" — fine.

Wait — careful with the eyebrow regex in test_the_form_sections_follow_the_agreed_order: it's health-check only. OK.

Now, the new section: which eyebrow/h2 wording? Let me follow the existing pattern on that page:

    Page heading: eyebrow "Saved results", h1 "History"
    Section: eyebrow "All checks", h2 "Saved health checks"
    Detail section: eyebrow "Read-only", h2 "Health check"

So a new export section could be:

    eyebrow: "Export"
    h2: "Download the report" — hmm. Or "CSV export"? The h2 is the title bar with the white text.

Hmm, "med eigen passande h2-del og info tekst". The h2 should be short. Let me use:

    eyebrow: "Export"
    h2: "Download the report"
    link: Download CSV
    info text: "Every saved key check is exported, one row per key check, as a dated CSV file. The file is named with the server's date."

Hmm, the previous note said: "Save a health check to see it in the history. Download CSV exports every saved key check, one row per key check, as a dated file." The first sentence is now redundant (it sits under the history list). So the info text should just explain the export.

Let me pick English UI text, short and concrete:

    eyebrow: Export
    h2: Download the report
    p (info): Every saved key check is exported as one row, as a dated CSV file. The filename carries the date the server answers.

Hmm, that's a bit wordy. Let me simplify: One row per saved key check, as a dated CSV file.

Hmm, but the original had "one row per key check, as a dated file" which the test pins: assertIn("one row per key check, as a dated file", html). I need to update that test anyway. Let me keep the wording close so the intent is preserved:

info text: Every saved key check is exported, one row per key check, as a dated CSV file.

Good, short, and keeps "one row per key check, as a dated ... file". Hmm, the original said "as a dated file" (not "dated CSV file"). Since the h2/eyebrow already say export/CSV, let me write:

Every saved key check is exported, one row per key check, as a dated CSV file.

Hmm, and maybe add the "not overwritten" flavour? No, keep it short.

Now, what about the CSS? The link is now inside a .section-block, not .page-heading. The .page-heading > .secondary-button rule would be dead. Options:
(a) Remove the rule and rely on .section-heading { margin-bottom: 10px; } + the link + the note. But then the button and the info text: the info text needs margin-top — .workflow-note has margin: 12px 0 0, so if I use p.workflow-note the spacing is fine. And the button sits right after the .section-heading div (block), so it's on its own line with the section-heading's 10px margin below. Good — no extra CSS needed.

So: remove .page-heading > .secondary-button { margin-top: 12px; } (dead) and don't add anything. Hmm, but should I keep it? It's dead code; the brief says don't leave dead selectors (they removed the dead history-card part earlier). I'll remove it and note that in the docs.

Hmm, wait: is .page-heading > .secondary-button used anywhere else? On other pages: setup.html's .page-heading has no button (the actions are in .form-actions); settings.html no; health-check.html no; login.html no; index.html no. So yes, dead → remove.

And the info text: use p.workflow-note (class already styled, margin: 12px 0 0) but without the id, since the user said the id can go. Actually the user said "p#workflow-note kan du fjerne" — remove the element with that id. So the new info text is a new element; I'll give it class="workflow-note" and no id. Hmm, should it have an id? Not needed. Keep it simple: <p class="workflow-note">…</p>.

Hmm, but .workflow-note has margin: 12px 0 0 — that gives air between the button and the text. Good, "info tekst" under the button.

Wait, actually — ordering: h2 title bar, then button, then info text? Or h2, then info text, then button? The user said: put "Download CSV" after "ALL CHECKS Saved health checks", with its own suitable h2 and info text. So the section is: eyebrow+h2, then presumably the button and the info text. Let me put: section-heading (eyebrow "Export" + h2 "Download the report"), then the link, then the info text. Hmm, or info text then button?

Looking at the page's other patterns: on the health-check form, a section is: eyebrow+h2, then help text, then fields, then actions. On the setup page: eyebrow+h2, help, then grid, then actions. So "info text then action" is the established order. Hmm.

But on the history page the previous arrangement was link then note. The user said "med eigen passande h2-del og info teskt" — they want the h2 part and the info text. Order isn't specified. I'll follow the page/site pattern: h2, then the info text, then the button. Hmm.

Hmm, but then the note and the button: the note is a help line above the action, which matches "a section is: heading, help, action". I think that reads best and matches the rest of the app.

Hmm, but the user earlier explicitly asked for the note under the button ("den må visast i history sida under «Download CSV» knappen"). That was about the note's placement relative to the button. Now they're restructuring the whole thing. To respect their earlier preference AND the new request... hmm, conflicting.

Their earlier instruction was explicit: the note goes under the button. Now they want a proper section with h2 + info text. I think the safest is to keep the note under the button (their explicit earlier wish) and put the h2 section around it: eyebrow+h2, then the button, then the info text. That satisfies both: own h2 part, info text, and the note stays under the button.

Hmm, but a help line above an action is more conventional... The user asked for "under knappen" explicitly last round, and this round they didn't revoke it. Keep it under the button. Good.

So new markup:
html
Skjul
Lagre
Kopier
Forhåndsvisning
1
2
3
4
5
6
7
8
9
10
11
12
13
⌄
⌄
⌄
      <!-- The export has a section of its own now, after the list: a title bar,
           the button, and the line that explains what the file holds
           (section 32.7 follow-up point 4). -->
      <section class="section-block" aria-labelledby="export-title">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Export</p>
            <h2 id="export-title">Download the report</h2>
          </div>
        </div>
        <a class="secondary-button" href="/api/export">Download CSV</a>
        <p class="workflow-note">Every saved key check is exported, one row per key check, as a dated CSV file.</p>
      </section>

And remove the link + note from .page-heading.

Hmm — wait. Where exactly does this section go? "etter 'ALL CHECKS Saved health checks'" — after that section. But the detail section (#history-detail) also comes after the list. Should the export go between the list and the detail? The user said "etter ALL CHECKS Saved health checks". I'll put it directly after the list section and before #history-detail. Hmm, but then when you click View, the detail opens below the export section, and the #history-detail anchor scrolls past the export block. That's fine.

Hmm, alternatively put it after the detail section (at the bottom of the page). "Etter All checks" suggests directly after. I'll put it directly after the list section, before the detail section. That's the literal reading.

Hmm, but consider UX: the export is a page-level action; putting it between the list and the detail means the detail appears below it. When the user clicks View, the page jumps to #history-detail, scrolling past the export. Acceptable.

Hmm, actually... maybe it reads better at the very end of the page (after the detail). But the user said after "Saved health checks". I'll do exactly that and mention it.

Now, tests to update:

tests/test_health_check_form.py:

    test_the_history_page_offers_the_export_and_the_note — currently asserts:
        link in html ✓
        assertNotIn("download=", html) ✓
        assertIn('id="workflow-note"', html) → must change (id gone)
        assertLess(html.index(link), html.index('id="workflow-note"')) → change to the note being after the link (still true, but I need a different marker for the note)
        assertIn("one row per key check, as a dated file", html) → the new text is "one row per key check, as a dated CSV file." → update
        assertIn(".page-heading > .secondary-button { margin-top: 12px; }", styles) → the rule is removed → replace with the new truth: the export has its own section with a title bar, and the link stands after the list section.

Let me rewrite that test as test_the_history_page_offers_the_export_in_its_own_section:
python
Skjul
Kjør
Lagre
Kopier
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
⌄
    def test_the_history_page_offers_the_export_in_its_own_section(self):
        # The export has a section of its own on the history page, after the list:
        # a title bar, the button, and the line that explains what the file holds
        # (section 32.7 follow-up point 4).
        html = read_static("history.html")

        list_title = 'id="history-list-title"'
        link = '<a class="secondary-button" href="/api/export">Download CSV</a>'
        export_title = 'id="export-title"'
        note = '<p class="workflow-note">Every saved key check is exported'
        self.assertIn(link, html)
        # No download attribute, so the dated filename from Content-Disposition is
        # the one that wins (section 31 point 3).
        self.assertNotIn("download=", html)
        # The section comes after the saved-check list, and it carries its own
        # title bar.
        self.assertLess(html.index(list_title), html.index(export_title))
        self.assertLess(html.index(export_title), html.index(link))
        self.assertIn('<p class="eyebrow">Export</p>', html)
        self.assertIn("<h2 id=\"export-title\">Download the report</h2>", html)
        # The line that explains the file stands under the button, and the old
        # free-standing note is gone.
        self.assertLess(html.index(link), html.index(note))
        self.assertIn("one row per key check, as a dated CSV file", html)
        self.assertNotIn('id="workflow-note"', html)
        self.assertNotIn("Save a health check to see it in the history. Download CSV exports", html)

Also .page-heading > .secondary-button removal: is it asserted anywhere else? In this test only. I'll drop that assertion (replaced by the section assertions).

Hmm, and the previous test_the_dashboard_has_no_next_check_card_and_no_history_block asserts assertNotIn("workflow-note", html) on index.html — still fine (index.html has none). And history.html now has class="workflow-note" but no id — fine.

Wait — careful! Is there any test asserting the history page has NO workflow-note? No.

Also tests/test_app.py::test_the_history_page_offers_the_csv_download asserts:
python
Skjul
Kjør
Lagre
Kopier
1
2
3
4
5
        self.assertIn(
            '<a class="secondary-button" href="/api/export">Download CSV</a>',
            body,
        )
        self.assertNotIn("download=", body)

Still passes. ✓

Any test that asserts the eyebrows on history.html exactly? Let me think... test_the_form_sections_follow_the_agreed_order → health-check.html only. test_the_settings_page_has_the_two_sections → settings.html. So adding an eyebrow on history.html is safe. But wait — is there any test that collects eyebrows from history.html? I don't recall one. Let me double check my written test file... searching my memory of the file I wrote: test_the_form_sections_follow_the_agreed_order (health-check), test_the_settings_page_has_the_two_sections (settings). No history eyebrow test. Good.

Hmm, one more: does test_the_pages_offer_one_way_back_to_the_dashboard or similar touch history? It checks NotIn "Back to dashboard" in history.html ✓.

So only tests/test_health_check_form.py needs the test change.

Files to change:

    static/history.html — remove the link+note from .page-heading, add the new export section after the list section.
    static/styles.css — remove the dead .page-heading > .secondary-button rule.
    tests/test_health_check_form.py — update the export test.
    TODO.md — record point 4, update §9 (and §8? no) and the test count.
    ai-note.md — same.

Test count: 513 stays 513 (one test renamed, no additions). Hmm, should I add a test for the removed .page-heading > .secondary-button rule? Not needed. So 513 tests, with one renamed.

Hmm, the count stays the same but the user asked to report "testtalet før og etter" — it stays 513. Since the user said "Ran 513 tests ok", after this change it's still 513. I'll say so.

Wait — should I add a test? The brief says "Legg til testar for det nye". The new thing is the export section. My updated test covers it. Fine, no new test needed; but hmm, the convention earlier was to add tests. I'll extend the existing test (renamed) with the new assertions — that's a real coverage increase without a count change. Fine.

Let me now write history.html.

New history.html:
html
Skjul
Lagre
Kopier
Forhåndsvisning
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
⌄
⌄
⌄
⌄
⌄
⌄
⌄
⌄
⌄
⌄
⌄
<!doctype html>
<html lang="en">
  <head>
    ... (unchanged, with robots meta)
  </head>
  <body>
    <header class="topbar">...</header>

    <main class="page-shell">
      <div class="page-heading form-heading">
        <div>
          <p class="eyebrow">Saved results</p>
          <h1>History</h1>
          <p class="intro">Every saved annual health check, newest first. Saved checks are never overwritten.</p>
        </div>
      </div>

      <section class="section-block" aria-labelledby="history-list-title">
        ... unchanged ...
      </section>

      <!-- The export has a section of its own, after the list: a title bar, the
           button, and the line that explains what the file holds
           (section 32.7 follow-up point 4). -->
      <section class="section-block" aria-labelledby="export-title">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Export</p>
            <h2 id="export-title">Download the report</h2>
          </div>
        </div>
        <a class="secondary-button" href="/api/export">Download CSV</a>
        <p class="workflow-note">Every saved key check is exported, one row per key check, as a dated CSV file.</p>
      </section>

      <section class="section-block" id="history-detail" aria-labelledby="history-detail-title" hidden>
        ... unchanged ...
      </section>
    </main>
    <footer class="footer"><span>VardKey</span></footer>
  </body>
</html>

Good.

Now styles.css: remove the .page-heading > .secondary-button rule and its comment.

Now the test file. I need to rewrite it (48KB) with the one test changed. Ugh, but necessary.

Let me do: history.html, styles.css, test file, TODO.md, ai-note.md = 5 files.

Let me start.