# H8-04: a Latin-1 JATS XML upload is kept with its units replaced

**Statement.** A JATS XML file that declares and uses ISO-8859-1 is decoded as UTF-8 with replacement
and answered `ingested` with no word, so its passage keeps "5 �g/L of furfural at 30 �C"
where the file says "5 µg/L of furfural at 30 °C"; the same Latin-1 bytes uploaded as Markdown are
answered `failed` in words.

**Contract.**
- `docs/api/intake.md:17`: "`upload` | a file a person uploads: PDF, Markdown, text, HTML or JATS XML, at most 50 MB"
- `docs/api/intake.md:52-54`: "`status` is `ingested` (stored in the kit for the first time), ... or `failed` with the `reason` in words"
- `core/openferment_core/literature/collectors.py:8-9`: "A file a person uploads (`upload`) and text a person pastes (`paste`) are taken as given."
- `core/openferment_core/literature/collectors.py:20-22`: "A split returns a `FetchResult` whose status is `failed:fetch` or `failed:parse` with a reason, and a collector raises `NotCollected` with that reason, which Intake shows as it stands."

An XML document's encoding declaration names how its bytes are read (XML 1.0 §4.3.3), so an
ISO-8859-1 JATS file is JATS XML the upload door takes. Taken as given, its words keep their units,
or the door refuses it in words as the Markdown door does.

**Command.** `bash bughunt/repro/H8-04/run.sh` from the repository root. It makes the fresh database
`bh_r_h8_04_latin1`, starts the head's service keyless on the first free port of 127.0.0.1:9050-9059,
makes the project `enc`, uploads three files (`probe.py`), reads the kit's chunk rows with psql, then
stops the service and drops the database. No model is called.

1. `assay.xml`: `<?xml version="1.0" encoding="ISO-8859-1"?>`, one JATS `<p>` reading
   "The supernatant held 5 µg/L of furfural at 30 °C after 48 h", encoded in ISO-8859-1 (µ is byte 0xB5, ° is 0xB0).
2. `assay.md`: the same sentence in Latin-1 as Markdown.
3. `assay-utf8.xml`: the same article declared and encoded as UTF-8 (the control).

**Expected.** `assay.xml` read in the encoding it declares, its passage keeping "5 µg/L of furfural at
30 °C" (the standard library's parser, handed the file's bytes, reads exactly that), or the file
answered `failed` with a reason, as `assay.md` is.

**Observed (run1.log, run2.log, alike).**
- `assay.xml`: `ingested`, no reason; the project's passage and the kit's chunk row (`sci_rag.chunks`)
  read `'The supernatant held 5 �g/L of furfural at 30 �C after 48 h in the H8-04 repro.'`:
  both non-ASCII characters replaced by U+FFFD, the micro prefix of the unit lost.
- `assay.md`: `failed | the kit did not store it: parse error: 'utf-8' codec can't decode byte 0xb5 in position 32: invalid start byte`.
- `assay-utf8.xml`: `ingested`, kept `5 µg/L ... 30 °C`.
- `RESULT: DEFECT` in both runs.

**Likely cause.** `core/openferment_core/literature/collectors.py:1688`
`xml = data.decode("utf-8", errors="replace")` turns the uploaded bytes into a string before the parse,
so `split_jats` (`collectors.py:1018`, `ET.fromstring(xml)`) and `jats_citation` (`collectors.py:1328`)
parse a string whose 0xB5 and 0xB0 bytes are already U+FFFD, and the declaration is never read.
Handing `ET.fromstring` the bytes lets expat read the declared encoding (the probe's second line shows it
reading "5 µg/L ... 30 °C"); a strict decode would refuse the file in words.
