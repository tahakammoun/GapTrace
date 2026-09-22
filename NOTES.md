# HTML parser check — dsgvo_art12/13/14.html

Parser under test: `src/ingest/parse_html.py` — decomposes `script/style/nav/header/
footer` tags, then `soup.get_text("\n", strip=True)`. Checked against all three raw
files in `data/raw/`. Structure claims below are cross-checked two ways: (1) counting
`<li>`/`<ol>` in the raw HTML, (2) fetching the live article at dsgvo-gesetz.de and
asking it to enumerate paragraphs/sub-points independently. Both agree.

## 0. Art. 13(1)(a) — is it "identity and contact details"?
**Yes, no off-by-one.** Raw HTML (`data/raw/dsgvo_art13.html:386`), first `<li>` under
the paragraph-1 `<ol>`: *"den Namen und die Kontaktdaten des Verantwortlichen sowie
gegebenenfalls seines Vertreters"* — the controller's (and rep's) name and contact
details. Confirmed against the live article at dsgvo-gesetz.de/art-13-dsgvo: paragraph
1, point (a) is exactly that. Position in the HTML list matches the legal citation.

## Per-article results

### Art. 12 — 8 paragraphs, only paragraph 5 is lettered (a, b)
- **Glued words:** gone. No `werdensollen` hit.
- **Boilerplate:** NOT gone — same leak as the others (see §2 below).
- **Umlauts/ß:** survive (91 occurrences in the parsed text, spot-checked correct).
- **Cross-references:** NOT single sentences — split at every `<a>` (e.g. `Artikel 34`,
  `Artikel 11`, `Artikel 92` each land on their own line).
- **Structure count:** raw HTML has one outer `<ol>` with 8 `<li>` (paragraphs 1–8);
  only paragraph 5 contains a nested list, and that nested list has 2 `<li>` (a, b —
  "ein angemessenes Entgelt verlangen" / "sich weigern, ... tätig zu werden").
  Confirmed live: 8 paragraphs, only §5 lettered, with exactly 2 points (a, b).
  **This is a very different shape from Art. 13/14** — mostly prose paragraphs, one
  small lettered exception. Do not expect a 6-and-6 pattern here.

### Art. 13 — 4 paragraphs, 6 lettered points under (1) and (2)
- **Glued words:** gone. No `werdensollen` hit; `werden sollen` (line 9) and
  `aussagekräftige Informationen` (line 33) are correctly spaced.
- **Boilerplate:** NOT gone (see §2).
- **Umlauts/ß:** survive (54 occurrences).
- **Cross-references:** NOT single sentences — e.g. text lines 10–12 read
  `wenn die Verarbeitung auf` / `Artikel 6` / `Absatz 1 Buchstabe f beruht, ...` as
  three separate lines instead of one sentence, because `Artikel 6` sits in an `<a>`
  and the `\n` separator breaks on every tag boundary, not just block tags.
- **Structure count:** matches expectation — outer `<ol>` has 4 `<li>` (paragraphs
  1–4); paragraph 1's nested `<ol>` has 6 `<li>` (a–f), paragraph 2's has 6 `<li>`
  (a–f), paragraphs 3 and 4 have no nested list. Confirmed live (4 paragraphs, 6+6).
  **Caveat:** this count only comes out right if you count `<li>` elements in the raw
  HTML. Counting *lines in the parsed text output* instead gives 30 lines for 16 real
  items, because two of the six items in each lettered paragraph contain a cross-
  reference link and get fragmented into 2–7 physical lines apiece (see the example
  above). A naive "count paragraphs by blank-adjacent line groups in the .txt" check
  would overcount and get the wrong number — the cross-reference bug (§4) and the
  structure-count check (§6) are the same root cause, not independent issues.

### Art. 14 — 5 paragraphs, 6/7/3/0/4 lettered points — different from Art. 13
- **Glued words:** gone. No `werdensollen` hit.
- **Boilerplate:** NOT gone (see §2).
- **Umlauts/ß:** survive (90 occurrences).
- **Cross-references:** NOT single sentences — same `Artikel 6` / `Artikel 9` /
  `Artikel 22` / `Artikel 46/47/49` / `Artikel 89` links each break their sentence.
- **Structure count:** outer `<ol>` has 5 `<li>` (paragraphs 1–5):
  - (1): nested `<ol>` with 6 `<li>` (a–f)
  - (2): nested `<ol>` with **7** `<li>` (a–g) — one more than Art. 13(2)
  - (3): nested `<ol>` with 3 `<li>` (a–c) — a paragraph shape Art. 13 doesn't have at all
  - (4): no nested list (plain provision, like Art. 13(3)/(4))
  - (5): nested `<ol>` with 4 `<li>` (a–d)
  Confirmed live: 5 paragraphs, sub-point counts 6/7/3/0/4. **This does not match the
  Art. 13 "4 paragraphs, 6-and-6" shape** — one more paragraph, one extra lettered
  point in (2), and an entirely extra lettered paragraph (3) for timing rules that
  Art. 13 folds into plain prose. Any curation tooling that hardcodes "6 letters per
  lettered paragraph" from the Art. 13 example will misfile Art. 14(2).

## Cross-cutting findings (same in all three files)

### 2. Navigation boilerplate — gone?
**No.** All three outputs open with:
```
Suche nach:
Zum Inhalt springen
Suche nach:
Impressum | Datenschutz | Haftung
```
None of this lives inside `<nav>`/`<header>`/`<footer>` in the source, so
`tag.decompose()` never reaches it:
- `Suche nach:` (×2) → two separate `<span class="screen-reader-text">` inside
  `<form role="search">` widgets — forms aren't in the blocklist.
- `Zum Inhalt springen` → `<a class="skip-link screen-reader-text" href="#content">`,
  sitting directly in `<body>`, outside any header/nav/footer.
- `Impressum | Datenschutz | Haftung` → `<aside id="text-3">` inside
  `<div id="widget-area" role="complementary">` — an aside, not a footer.
Separately, the page's XING/LinkedIn footer links (`<li>` at the very end of the
file) *are* correctly stripped — they sit inside a real `<footer id="colophon">`,
confirming `decompose()` works when the boilerplate is tagged correctly; the problem
is only the boilerplate that the WordPress theme puts outside those tags.
The blocklist needs to grow (by role/class, e.g. `role="complementary"`,
`.screen-reader-text`, `.skip-link`, `form.search-form`) or this needs a
main-content-selector approach (e.g. grab `<article>`/`.entry-content` instead of
subtracting known-bad tags from the whole page).

### 3. / 4. Cross-references — intact as single sentences?
**No, in all three files.** Every legal cross-reference (`Artikel 6`, `Artikel 9`,
`Artikel 22`, `Artikel 34`, `Artikel 46/47/49`, `Artikel 89`, `Artikel 92`, `Artikel
11`) is wrapped in an `<a href="...">` in the source. `get_text("\n", strip=True)`
inserts a newline at *every* tag boundary, so each link's text is pushed onto its own
line and the sentence around it is split into pieces, e.g.:
```
wenn die Verarbeitung auf
Artikel 6
Absatz 1 Buchstabe f beruht, die berechtigten Interessen, ...
```
This is the flip side of the glued-word fix (§1): joining with `"\n"` stopped words
gluing together (previously joining with `""`), but it now also hard-breaks around
every inline element. A single separator string can't distinguish "inline, join with
a space" from "block-level, join with a newline" — fixing this needs a custom
text-extraction walk (treat `<a>`, `<span>`, `<sup>`, etc. as inline and join with `" "`
or nothing plus normalization; treat `<li>`, `<p>`, `<ol>` as block and join with
`"\n"`), not a single `get_text(sep)` call.

### 5. Umlauts and ß — survive?
**Yes, confirmed again**, consistently across all three files (54–91 occurrences
each, spot-checked: `Löschung`, `Rechtmäßigkeit`, `Widerspruchsrecht`, `Auskunft`,
`Übermittlungen`, `Geheimhaltungspflicht`). `parse_html` reads with
`encoding="utf-8"`, matching the source `<meta charset>`, so no mangling.

## Fix — Art. 12(5) silently dropped in `src/ingest/parse_article.py`

`parse_article` (new structured extractor, walks `<ol>/<li>` directly instead of
relying on `get_text(sep)`, so cross-references land intact as single sentences —
see §3/§4 above) was returning only 7 items for Art. 12 instead of 9: refs jumped
from `Art. 12(4)` straight to `Art. 12(6)`.

Cause: the source HTML double-wraps Art. 12(5)'s sublist in two nested `<ol>` tags
with no `<li>` at the outer level:
```html
<li>  <!-- paragraph 5 -->
  ...text, <sup>, <a> links...
  <ol>            <!-- outer wrapper, 0 direct <li> -->
    <ol>          <!-- inner list, has the 2 real <li> -->
      <li>ein angemessenes Entgelt verlangen...</li>
      <li>sich weigern, aufgrund des Antrags tätig zu werden.</li>
    </ol>
  </ol>
  <p>...</p>
</li>
```
`para.find("ol", recursive=False)` grabbed the outer wrapper; `.find_all("li",
recursive=False)` on it came back empty; the paragraph silently produced zero
entries with no error. Confirmed by reproducing the DOM directly in a REPL before
touching the code.

Fix — drill through empty `<ol>` wrappers until one with real `<li>` children is
found, and raise instead of returning nothing if the wrapping runs out:
```python
def _item_list(para):
    """Find the <ol> holding this paragraph's lettered items, drilling
    through any empty wrapper <ol> (e.g. Art. 12(5) double-wraps its
    sublist with no <li> at the outer level)."""
    ol = para.find("ol", recursive=False)
    while ol is not None and not ol.find_all("li", recursive=False):
        inner = ol.find("ol", recursive=False)
        if inner is None:
            raise ValueError(f"<ol> with no <li> and no nested <ol> under: {para}")
        ol = inner
    return ol
```
`nested = para.find("ol", recursive=False)` in `parse_article` became
`nested = _item_list(para)`.

Verified after the fix: Art. 12 → 9 items (was 7), adding `Art. 12(5)(a)` "ein
angemessenes Entgelt verlangen..." and `Art. 12(5)(b)` "sich weigern...". Art. 13
(14 items) and Art. 14 (21 items) unchanged, as expected since the bug was specific
to Art. 12's double-wrapped list. `ruff check` clean.

## Net takeaway
Two real bugs remain, and they're linked: the tag-name-only blocklist misses
boilerplate that isn't tagged `nav`/`header`/`footer` (§2), and the single `"\n"`
separator over-breaks at every inline tag including cross-reference links (§3/§4).
Both point to the same fix direction: stop subtracting known-bad tags from the whole
page and instead (a) extract from a scoped main-content container, and (b) walk the
tree distinguishing inline vs. block elements for the join separator, rather than one
global `get_text(sep, strip=True)` call. Structural counts (§6) are correct at the
`<li>` level for all three articles and match the live article text, including the
two places (Art. 12, Art. 14) that don't follow the Art. 13 "4 paragraphs / 6-and-6"
shape — but that check is only reliable when counting `<li>` in the HTML, not lines
in the current parser's text output, since the cross-reference bug fragments some
items into multiple lines.
## Splitting rule (decided <18/09/2026>)

One requirement = one Obligation or Condition a reviewer could tick off independently.

- A lettered point naming two distinct pieces of information is split.
- Conditional obligations ("gegebenenfalls") stay one requirement; the condition goes
  into the text.
- The paragraph's introductory sentence is folded into each sub-requirement so it stands
  alone.
- Procedural duties (Fristen, Form) are separate from content duties.
## Catalog v1 frozen <date>
- ~60 requirements from DSGVO Art. 12-14
- File shape (requirements/dsgvo_art12_14.jsonl): {key, ref, legal_text, requirement,
  condition, obligation, category, ref_verified}
- Database shape (requirements table): same fields, with `requirement` stored in the
  `text` column — mapped once, in src/requirements/load.py, and nowhere else
- legal_text verified against EUR-Lex consolidated text; text is the checkable
  paraphrase used for embedding and matching
- ~8 rows carry an explicit `condition` (consent-based, legitimate-interest-based,
  repurposing, third-country transfer); findings on these get `applicability` set
  before status is decided
- Dropped: Art. 12(2)-(6) and 12(8) (request-handling process, not document content),
  14(3) and 14(5) (timing rules and exemptions, not checkable against document text),
  art12_1_muendliche_information (a permission on the controller, "kann" not "muss",
  and not observable in a written document)
- Known limitation: no per-requirement check-type dispatcher. All requirements are
  checked the same way (retrieve + classify + verify quote), even though some
  (e.g. icon presence) would suit a different check shape. Not built — scale does not
  justify it yet.
- Splitting rule: see above
- Changing this catalog invalidates every measurement taken against it. If it must
  change, bump version to v2.