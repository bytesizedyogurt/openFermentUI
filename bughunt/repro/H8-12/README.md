# H8-12: an SFF file with a UTF-8 byte-order mark is refused as "not JSON" (refuted)

**Statement (the candidate's).** A UTF-8 SFF file with a byte-order mark is refused at
`POST /api/flowsheets/import` with "is not JSON: its text stops reading as JSON at line 1, column 1",
while the catalogue door (`POST /api/intake/catalogue`) reads the same mark (utf-8-sig) and keeps its file.

**Verdict: not reproduced as a defect.** Both runs show the behaviour the candidate describes, and both
end `RESULT: NO-DEFECT`. The refusal falls on one of the grounds the contract itself names ("not JSON"),
and the toolkit that checks every kept file reads no graph from the same bytes.

## Contract

`docs/api/sff.md:43-45`: "A file is refused only when no graph can be read from it: not UTF-8, not JSON,
or not an object with a list of units and a list of streams (422), or larger than 16 MB (413)."

The words are quoted correctly. They list "not JSON" as a ground for refusal, and a text that begins with
U+FEFF is outside JSON's grammar: RFC 8259 §8.1 says a writer "MUST NOT add a byte order mark" and a
parser "MAY ignore the presence of a byte order mark rather than treating it as an error", so treating it
as an error is the RFC's other permitted choice. No contract ties the SFF door's decoding to the catalogue
door's; `docs/api/intake.md:104` says nothing of a byte-order mark either.

## Command

```
bash bughunt/repro/H8-12/run.sh
```

A fresh database `bh_r_h8_12_svc`, the head's service on 127.0.0.1:10110, keyless, no model call. It posts
`marked.json` (EF BB BF, then `{"units": [], "streams": [], "metadata": {"process_title": "BOM"}}`) to the
import door and `marked.csv` (EF BB BF, then `id,name` / `S1,One`) to the catalogue door, stops the
service, and then runs the worker's own check (`openferment_core.workers.sff_toolkit.validation` and
`completeness`, the functions the worker's `sff_validate` and `sff_score` ops call) on the same flowsheet
bytes with and without the mark. It drops the database and removes its files on exit. About 25 s.

## Expected

The contract holds when the refused file is outside JSON's grammar and no reader in the tree reads a
graph from it. It breaks when the toolkit, which receives every kept file byte for byte, reads a graph
from bytes the door refused. The candidate expected the file kept, or refused in words naming the mark.

## Observed (run1.log and run2.log, identical verdicts)

- Import door: HTTP 422 `{"detail":"marked.json is not JSON: its text stops reading as JSON at line 1, column 1"}`.
- Catalogue door: HTTP 200 `{"kind":"strain","kept":["S1"],"refused":[]}`.
- The worker's check on the flowsheet without the mark: read (valid False, 29 findings, completeness 0.000).
- The worker's check on the same bytes with the mark: `JSONDecodeError: Unexpected UTF-8 BOM (decode using
  utf-8-sig): line 1 column 1 (char 0)`.
- `RESULT: NO-DEFECT`, both runs.

## Cause of the behaviour, and why it stands

- `core/openferment_core/engine/sff.py:379` decodes with `"utf-8"`, which keeps U+FEFF, and `:383`
  `json.loads` refuses it; `:385` words the refusal by place alone.
- `core/openferment_core/engine/sff.py:580-585` writes the bytes as they came to `flowsheet.json` and hands
  that path to the toolkit; `core/openferment_core/workers/sff_toolkit.py:65-69` passes it to
  `pisces_sff.validate_flowsheet_against_SFF`, which opens it at
  `core/vendor/pisces_sff/validate/_validate.py:1750-1751` with `encoding='utf-8'` and `json.load`, and
  raises on the mark. A door that read the mark would hand the worker a file it cannot open, or would have
  to strip the mark and break "the file is kept byte for byte" (`docs/api/sff.md`, the `sha256, bytes` row).
- `core/openferment_core/catalogues.py:527` decodes with `"utf-8-sig"`: a separate door for spreadsheet
  exports, whose CSV files commonly carry the mark.

What remains is wording, S4 at most and outside any stated contract: the refusal gives the place
(line 1, column 1) and leaves out the reason Python's `json` gives ("Unexpected UTF-8 BOM"), the same
words a file of plain garbage gets. Naming the mark in the refusal would be a one-line change at
`core/openferment_core/engine/sff.py:385` (passing `e.msg` through), should the owner want it.
