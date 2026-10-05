import json

PROMPT = """Du prüfst, ob eine Bedingung für ein Dokument zutrifft.

BEDINGUNG: {condition}
BEDEUTUNG: {description}

AUSZÜGE AUS DEM DOKUMENT:
{passages}

Trifft die Bedingung auf dieses Dokument zu, basierend auf den Auszügen?
- "applicable": Ja, die Bedingung trifft klar zu (z.B. das Dokument erwaehnt
  Einwilligung als Rechtsgrundlage).
- "not_applicable": Nein, die Bedingung trifft klar nicht zu.
- "unknown": Aus den Auszügen laesst sich das nicht sicher entscheiden.

Wenn KEIN Auszug die Bedingung erwaehnt, unterscheide WARUM:
- Wenn ein normales Dokument diese Bedingung erwaehnen WUERDE, sofern sie zutrifft
  (z.B. eine Zielgruppe von Kindern, automatisierte Entscheidungsfindung, ein
  bestellter Datenschutzbeauftragter -- das sind Dinge, die Unternehmen aus
  rechtlichen Gruenden typischerweise offenlegen, wenn sie zutreffen), dann ist
  das Schweigen selbst ein Hinweis: "not_applicable", nicht "unknown".
- Wenn die Bedingung etwas beschreibt, das aus TEXT allein prinzipiell nicht
  erkennbar ist (z.B. ob Piktogramme/Icons visuell verwendet werden -- das ist
  eine visuelle Eigenschaft, die beim Text-Extrahieren verloren geht), bleibt
  "unknown" die ehrlichere Antwort, auch wenn kein Auszug es erwaehnt.

Antworte NUR mit JSON: {{"applicability": "...", "rationale": "ein Satz"}}
"""


# The catalog stores conditions as terse machine strings; the model was left to guess
# what they mean, and guessed wrong in ways the eval caught: "new purpose" read as
# "any purpose beyond the main one", a blanket "no transfers without safeguards"
# disclaimer read as "no third-country transfer" despite named US vendors, and consent
# checked only against the main processing.
CONDITION_DESCRIPTIONS = {
    "audience == 'children'": (
        "Trifft zu, wenn der Dienst oder die Datenschutzhinweise sich speziell an Kinder "
        "richten."
    ),
    "uses_pictograms == true": (
        "Trifft zu, wenn die Hinweise standardisierte Bildsymbole/Icons neben dem Text "
        "verwenden."
    ),
    "pictograms_electronic == true": (
        "Trifft zu, wenn solche Bildsymbole elektronisch dargestellt werden."
    ),
    "has_representative == true": (
        "Trifft zu, wenn ein Vertreter nach Art. 27 DSGVO benannt ist (fuer Verantwortliche "
        "ausserhalb der EU). Ein Geschaeftsfuehrer oder Ansprechpartner ist KEIN Vertreter."
    ),
    "has_dpo == true": (
        "Trifft zu, wenn ein Datenschutzbeauftragter bestellt bzw. genannt ist."
    ),
    "processing_basis == 'legitimate_interest'": (
        "Trifft zu, wenn IRGENDEINE Verarbeitung im Dokument auf berechtigtem Interesse "
        "(Art. 6 Abs. 1 lit. f DSGVO) beruht -- nicht nur die Hauptverarbeitung."
    ),
    "has_recipients == true": (
        "Trifft zu, wenn Daten an irgendwelche Dritte, Dienstleister oder "
        "Auftragsverarbeiter weitergegeben werden."
    ),
    "third_country_transfer == true": (
        "Trifft zu, wenn IRGENDEIN genannter Empfaenger oder Dienstleister Daten ausserhalb "
        "der EU/des EWR verarbeitet (z.B. ein US-Unternehmen) -- auch wenn das Dokument "
        "zugleich sagt, Uebermittlungen faenden nur mit Garantien statt."
    ),
    "processing_basis == 'consent'": (
        "Trifft zu, wenn IRGENDEINE Verarbeitung im Dokument auf Einwilligung beruht "
        "(z.B. Newsletter, Marketing-Cookies) -- nicht nur die Hauptverarbeitung."
    ),
    "automated_decision_making == true": (
        "Trifft nur zu bei ausschliesslich automatisierten Entscheidungen mit rechtlicher "
        "oder aehnlich erheblicher Wirkung (Art. 22 DSGVO). Werbe-Personalisierung oder "
        "Nutzungsanalyse zaehlen NICHT."
    ),
    "further_processing_new_purpose == true": (
        "Trifft nur zu, wenn Daten, die fuer einen Zweck erhoben wurden, SPAETER fuer "
        "einen anderen Zweck weiterverarbeitet werden sollen, der bei der Erhebung nicht "
        "genannt wurde. Zwecke, die das Dokument von vornherein nennt (auch Werbung), "
        "zaehlen NICHT."
    ),
}


def build(condition: str, chunks: list[dict]) -> str:
    passages = "\n\n".join(f"[{i}] {c['content']}" for i, c in enumerate(chunks, 1))
    description = CONDITION_DESCRIPTIONS.get(condition, "(keine Beschreibung)")
    return PROMPT.format(condition=condition, description=description, passages=passages)


def parse(raw: str) -> dict:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return {
            "applicability": "unknown",
            "rationale": f"Unparsable model response: {raw[:300]!r}",
        }
