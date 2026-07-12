# Report Schema

Two HTML reports, rendered by **one script from one JSON**. That is not a stylistic preference. Two renderers reading the same data will eventually disagree with each other, and the author will have no way to tell which one is lying.

The Excel workbook that earlier versions of this skill produced has been retired. HTML is what people actually read, it carries live links, and it needs no spreadsheet application.

## Report 1: Audit trail

Four columns, one row per reference, sorted worst-first.

| Column | Holds |
|:---|:---|
| Original | The citation as the `.bib` currently renders it, plus the key, entry type, and where it is cited. |
| Assistant | Where it searched, the link it found, and its fetch note. |
| Associate | The link status, the corroborating source if the fetch was blocked, what it corrected in the Assistant's record, and its note. |
| PI | Severity badge, final status, the ruling, the spot-check note if the PI checked it personally, and the confirmed discrepancies. |

The point of four columns is that the reader can see **the disagreements between the tiers**. When the Associate overturned the Assistant, both versions are on the page.

## Report 2: Comparison

Three columns, sorted worst-first. This is the one people actually act on.

| Column | Holds |
|:---|:---|
| Original | The citation as the `.bib` has it. |
| Corrected | The citation as the authoritative source has it. If the work was not found, say so plainly here, and do not put a guess in this column. |
| Explanation | Severity badge, the PI ruling, and the confirmed discrepancies. |

Row colours:

- **Red**: needs the author's attention (`needs_author_review` or `not_found`).
- **Amber**: `not_independently_verifiable`. Real, but not confirmable at an authoritative source. **This is not an error** and the report must not imply that it is.
- **Green**: confirmed correct. Any notes on a green row are cosmetic.

## Final statuses

- `verified`
- `not_found`
- `not_independently_verifiable`
- `needs_author_review`

## Severity

Severity answers "how much should the author care," which is a different question from "what is the status."

- `critical`: the citation points at the **wrong work**. Must be fixed before submission.
- `major`: metadata is wrong in a way a reader or copyeditor would catch.
- `decision`: nothing is wrong. The author must choose, for example whether to cite the published version of a working paper.
- `minor`: cosmetic. A missing DOI, exporter junk in a field, a capitalisation difference.
- `clean`: no discrepancy worth the author's time.

## The hygiene panel

Both reports carry it. It reports, without fixing:

- **Duplicate `.bib` keys**, and critically, **which of them actually print**. BibTeX keeps the first copy. If the first copy of a duplicated key is the less complete one, the bibliography is silently rendering the worse version, and the panel must say so.
- Entries with **missing required fields** for their type.
- **How many `.bib` entries are never cited**, since those never print and were not verified.
- Anything structurally odd about the `.bib` that would trip another tool, such as an entry indented before its `@`.

Distinguish a **latent** problem from an **active** one. A duplicate whose first copy drops a journal name is only a live bug if that key is actually cited. If it is not cited, say it is a trap for a future draft, not a present error. Overstating a finding costs credibility on all the others.

## Layout rules

These are not preferences. Each one was arrived at by getting it wrong first.

**`table-layout: fixed`, plus an explicit `<colgroup>` with percentage widths, plus `overflow-wrap: break-word` on every text-bearing cell.** All three, together. Without them a long DOI or URL blows the column widths out and the page scrolls sideways.

**Exactly one `position: sticky` element per page: the `<thead>`, at `top: 0`.** Never two. Two stickies with a hardcoded offset break the moment the first one's real rendered height differs from the assumed one, and the row underneath hides behind it.

**No scroll container. The page scrolls.** Do not put the table inside a `max-height` and `overflow: auto` pane. It was built that way once, and the reader's verdict was that it made the report unreadable: you scroll the page and nothing moves, you scroll the pane and lose your place. With rows that run several hundred words, it turns a document into an inbox.

If a future change appears to need a scroll container, the change is wrong. **Make the rows shorter instead.**

**Rows are tall, so give them room.** Generous cell padding, a visible border between references, and a base font size that is comfortable to read continuously. This is a document to be read, not a grid to be scanned.

**Theme-aware and self-contained.** Support light and dark. No external stylesheets, no CDN fonts, no remote images, no JS framework. The reading guide belongs behind a native `<dialog>`, which costs zero space until it is clicked.

## Changed versus unchanged

Decide it **on the rendered citation strings**, not on proxy metadata fields.

Build the original citation string and the corrected citation string, and compare those, because the rendered strings are what the reader actually sees. A metadata-level check can pass while the two visible columns plainly disagree with each other, and then the report contradicts itself in front of the author.

## Attribution byline

One small italic line under the title, giving the **date**, the **purpose**, and:

- the **author** of the paper, meaning the person running the skill. **Ask for this. Never guess, and never omit it.**
- a credit to `super-RA`, https://github.com/Mamooralikhan/super-RA
- a plain disclosure that **Claude Code** was used, naming the model

Keep it to one line. A large attribution banner reads as clutter to a reviewer.
