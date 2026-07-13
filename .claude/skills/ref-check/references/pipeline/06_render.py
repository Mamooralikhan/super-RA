#!/usr/bin/env python3
"""
STEP 06 of the bibliography verification pipeline. See scripts/00_README.md for run order.

Consumes : bib_verification/data/05_pi_review.json
           bib_verification/data/01_references.json   (hygiene panel)
Produces : reports/bibliography_audit.html        -- 4-col audit trail (Original/Assistant/Associate/PI)
           reports/bibliography_comparison.html   -- 3-col red/green (Original/Corrected/Explanation)

BOTH REPORTS ARE RENDERED HERE, FROM THE SAME JSON, BY THE SAME CODE. That is deliberate: two
renderers reading the same data will eventually disagree with each other, and the author would
have no way to tell which one lied.

CHANGED-vs-UNCHANGED IS DECIDED ON THE RENDERED CITATION, NOT ON PROXY METADATA FIELDS. We build
the original citation string and the corrected citation string, and diff those -- because the
rendered strings are what the reader actually sees. A metadata-level check can pass while the two
visible columns plainly disagree.

LAYOUT RULES. Each of these is a scar; do not undo one without reading why it is here.

  * THE PAGE SCROLLS. THE TABLE DOES NOT SCROLL INSIDE A BOX.
    The first version of this report put the table in a `max-height: 78vh; overflow: auto` pane.
    That turns a document into an inbox: you scroll the page and nothing moves, you scroll the
    pane and lose your place. With rows this long -- some explanations run several hundred words
    -- it was genuinely unreadable, and the author said so. There is no scroll container here.
    If a future change seems to need one, it is the wrong change: make the rows shorter instead.

  * EXACTLY ONE position:sticky element on the page: the <thead>, at top:0.
    It sticks to the VIEWPORT as the page scrolls normally. It is a thin header bar, not a pane,
    and it traps nothing. It earns its place because once you are deep inside a tall row you can
    no longer tell which column you are reading. Never add a second sticky element: two stickies
    with a hardcoded offset break the moment the first one's real height differs from the
    assumed one, and the row underneath hides behind it.

  * table-layout:fixed + explicit <colgroup> + overflow-wrap:break-word on every text cell.
    Without all three, a long DOI or URL blows the column widths out and the page scrolls sideways.

  * Attribution is one small italic byline. The reading guide lives behind a native <dialog>, so
    it costs zero space until clicked and needs no JS framework.
"""

import argparse
import html
import json
import re

import bst_render
from datetime import date
from pathlib import Path

SEV_LABEL = {
    "critical": "Critical",
    "major": "Major",
    "decision": "Your call",
    "minor": "Minor",
    "clean": "Clean",
}
STATUS_LABEL = {
    "verified": "Verified",
    "not_found": "Not found",
    "not_independently_verifiable": "Not independently verifiable",
    "needs_author_review": "Needs author review",
}
LINK_LABEL = {
    "resolved_and_matched": "Link opened and matched",
    "blocked_corroborated": "Publisher blocked the fetch; corroborated at a second source",
    "mismatch": "Link opens the WRONG WORK",
    "dead": "Link does not resolve",
    "no_link": "No link (nothing found to link to)",
}


def e(x):
    return html.escape(str(x) if x is not None else "")


def fmt_authors(authors, limit=None):
    """Render an author list. Keeps published ORDER -- never sorts."""
    if not authors:
        return ""
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(" and ") if a.strip()]
    authors = [a for a in authors if a]
    shown = authors if limit is None or len(authors) <= limit else authors[:limit]
    out = ", ".join(shown)
    if limit is not None and len(authors) > limit:
        out += f", et al. [{len(authors)} authors]"
    return out


# --------------------------------------------------------------------------------------------
# RENDERING IN THE PAPER'S OWN BIBLIOGRAPHY STYLE.
#
# Filled in by main() from bst_render, which drives the author's REAL .bst through BibTeX. When
# it is populated, every citation in both reports is printed exactly as the paper prints it, in
# aer or apsr or chicago or whatever the paper declares. When it is empty (no BibTeX on the
# machine, or the .bst is missing) we fall back to the generic format below AND SAY SO in the
# report. A report that silently changes format is worse than one that never offered the feature.
# --------------------------------------------------------------------------------------------
STYLED = {}          # key -> {"original": html, "corrected": html}
STYLE_NOTE = ""      # one plain sentence telling the reader which of the two they are looking at


def bibtex_from_bib(key, entry_type, f):
    """Rebuild the author's entry as BibTeX, so their own .bst can format it."""
    fields = {k: v for k, v in (f or {}).items() if v and k not in ("_raw",)}
    body = ",\n  ".join(f"{k} = {{{v}}}" for k, v in fields.items())
    return f"@{entry_type or 'article'}{{{key},\n  {body}\n}}"


def bibtex_from_verified(key, entry_type, m):
    """Rebuild the SOURCE OF RECORD's version as BibTeX, so it goes through the same .bst.

    Both columns must be formatted by the same style file. If they were not, a difference in
    FORMATTING would look to the reader like a difference in the DATA, and the report would be
    accusing the author of an error that only exists in our renderer.
    """
    if not m or not (m.get("title") or m.get("authors")):
        return None
    authors = m.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(" and ") if a.strip()]
    fields = {}
    if authors:
        fields["author"] = " and ".join(authors)
    for src, dst in (("title", "title"), ("year", "year"), ("venue", "journal"),
                     ("volume", "volume"), ("issue", "number"), ("pages", "pages"),
                     ("doi", "doi")):
        if m.get(src):
            fields[dst] = str(m[src])
    body = ",\n  ".join(f"{k} = {{{v}}}" for k, v in fields.items())
    return f"@{entry_type or 'article'}{{{key},\n  {body}\n}}"


def cite_from_bib(f):
    """The citation as the author's .bib currently renders it."""
    bits = []
    if f.get("author"):
        bits.append(fmt_authors(f["author"], limit=6))
    if f.get("year"):
        bits.append(f"({f['year']})")
    if f.get("title"):
        bits.append(f"&ldquo;{e(f['title'])}.&rdquo;")
    venue = f.get("journal") or f.get("booktitle") or f.get("institution") or f.get("publisher")
    if venue:
        bits.append(f"<em>{e(venue)}</em>" if not isinstance(venue, list) else "")
    tail = []
    if f.get("volume"):
        tail.append(f"{f['volume']}")
    if f.get("number") or f.get("issue"):
        tail.append(f"({f.get('number') or f.get('issue')})")
    if f.get("pages"):
        tail.append(f": {f['pages']}")
    if tail:
        bits.append("".join(tail))
    return " ".join(b for b in bits if b)


def cite_from_verified(m):
    """The citation as the AUTHORITATIVE SOURCE says it should read."""
    if not m or not (m.get("title") or m.get("authors")):
        return ""
    bits = []
    if m.get("authors"):
        bits.append(fmt_authors(m["authors"], limit=6))
    if m.get("year"):
        bits.append(f"({m['year']})")
    if m.get("title"):
        bits.append(f"&ldquo;{e(m['title'])}.&rdquo;")
    if m.get("venue"):
        bits.append(f"<em>{e(m['venue'])}</em>")
    tail = []
    if m.get("volume"):
        tail.append(f"{m['volume']}")
    if m.get("issue"):
        tail.append(f"({m['issue']})")
    if m.get("pages"):
        tail.append(f": {m['pages']}")
    if tail:
        bits.append("".join(tail))
    return " ".join(b for b in bits if b)


def link(u, text=None):
    if not u:
        return '<span class="muted">no link</span>'
    return f'<a href="{e(u)}" target="_blank" rel="noopener">{e(text or u)}</a>'


CSS = """
:root{
  --bg:#ffffff; --fg:#16181d; --muted:#666e7a; --line:#e3e6ea; --head:#f6f7f9;
  --red-bg:#fdf0f0; --red-line:#e5b4b4; --red-fg:#8a1f1f;
  --green-bg:#f1f8f2; --green-line:#b9d8bf; --green-fg:#1f6330;
  --amber-bg:#fdf6ec; --amber-line:#e6cfa4; --amber-fg:#8a5a12;
  --grey-bg:#f4f5f7;
  --accent:#1a4f8a;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#14161a; --fg:#e6e8ec; --muted:#9aa3af; --line:#2b2f36; --head:#1c1f25;
    --red-bg:#2b1618; --red-line:#6b2f31; --red-fg:#f2a7a7;
    --green-bg:#152218; --green-line:#2f5c3c; --green-fg:#9fd6ae;
    --amber-bg:#2a2013; --amber-line:#6b5322; --amber-fg:#e6c483;
    --grey-bg:#1b1e23;
    --accent:#7fb2ee;
  }
}
:root[data-theme="dark"]{
  --bg:#14161a; --fg:#e6e8ec; --muted:#9aa3af; --line:#2b2f36; --head:#1c1f25;
  --red-bg:#2b1618; --red-line:#6b2f31; --red-fg:#f2a7a7;
  --green-bg:#152218; --green-line:#2f5c3c; --green-fg:#9fd6ae;
  --amber-bg:#2a2013; --amber-line:#6b5322; --amber-fg:#e6c483;
  --grey-bg:#1b1e23; --accent:#7fb2ee;
}
:root[data-theme="light"]{
  --bg:#ffffff; --fg:#16181d; --muted:#666e7a; --line:#e3e6ea; --head:#f6f7f9;
  --red-bg:#fdf0f0; --red-line:#e5b4b4; --red-fg:#8a1f1f;
  --green-bg:#f1f8f2; --green-line:#b9d8bf; --green-fg:#1f6330;
  --amber-bg:#fdf6ec; --amber-line:#e6cfa4; --amber-fg:#8a5a12;
  --grey-bg:#f4f5f7; --accent:#1a4f8a;
}
*{box-sizing:border-box}
body{
  margin:0; padding:28px 22px 60px;
  background:var(--bg); color:var(--fg);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  overflow-wrap:break-word;
}
.wrap{max-width:1560px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.01em}
.byline{font-style:italic;color:var(--muted);font-size:.85rem;margin:0 0 18px}
.byline a{color:var(--accent)}
h2{font-size:1.05rem;margin:30px 0 10px}
p{margin:.5em 0}
a{color:var(--accent)}
.muted{color:var(--muted)}
button.guide{
  font:inherit;font-size:.8rem;padding:4px 11px;border:1px solid var(--line);
  border-radius:999px;background:var(--head);color:var(--fg);cursor:pointer;
}
button.guide:hover{border-color:var(--accent)}
dialog{
  max-width:640px;width:calc(100% - 40px);border:1px solid var(--line);border-radius:10px;
  background:var(--bg);color:var(--fg);padding:22px 24px;
}
dialog::backdrop{background:rgba(0,0,0,.45)}
dialog h3{margin:0 0 10px;font-size:1.05rem}
dialog ul{padding-left:18px;margin:.4em 0}
dialog li{margin:.35em 0}
dialog .close{margin-top:14px}

/* Summary tiles */
.tiles{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 6px}
.tile{
  flex:1 1 150px;border:1px solid var(--line);border-radius:8px;
  padding:10px 12px;background:var(--head);
}
.tile .n{font-size:1.5rem;font-weight:650;line-height:1.15}
.tile .l{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.tile.crit{background:var(--red-bg);border-color:var(--red-line)}
.tile.crit .n{color:var(--red-fg)}
.tile.ok{background:var(--green-bg);border-color:var(--green-line)}
.tile.ok .n{color:var(--green-fg)}
.tile.warn{background:var(--amber-bg);border-color:var(--amber-line)}
.tile.warn .n{color:var(--amber-fg)}

.tablewrap{
  border:1px solid var(--line); border-radius:8px; overflow:hidden;
}
table{width:100%;border-collapse:collapse;table-layout:fixed}
thead th{
  position:sticky; top:0; z-index:2;
  background:var(--head); text-align:left;
  font-size:.74rem; text-transform:uppercase; letter-spacing:.05em; color:var(--muted);
  padding:11px 14px; border-bottom:2px solid var(--line);
  box-shadow:0 1px 0 var(--line);
}
tbody td{
  padding:18px 14px; border-bottom:1px solid var(--line); vertical-align:top;
  font-size:.92rem; line-height:1.6; overflow-wrap:break-word; word-break:break-word;
}
/* A visible gap between references. With rows this tall, the row boundary is the main thing
   keeping them apart. */
tbody tr{border-top:3px solid var(--bg)}
tbody tr:last-child td{border-bottom:none}
tbody tr.red td{background:var(--red-bg)}
tbody tr.green td{background:var(--green-bg)}
tbody tr.amber td{background:var(--amber-bg)}
code,.key{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:.8em; background:var(--grey-bg); padding:1px 5px; border-radius:4px;
  overflow-wrap:break-word;
}
.badge{
  display:inline-block;font-size:.68rem;font-weight:600;padding:2px 7px;border-radius:999px;
  border:1px solid var(--line); white-space:nowrap; margin-bottom:5px;
}
.b-critical{background:var(--red-bg);border-color:var(--red-line);color:var(--red-fg)}
.b-major{background:var(--amber-bg);border-color:var(--amber-line);color:var(--amber-fg)}
.b-decision{background:var(--amber-bg);border-color:var(--amber-line);color:var(--amber-fg)}
.b-minor,.b-clean{background:var(--green-bg);border-color:var(--green-line);color:var(--green-fg)}
.note{margin:5px 0 0}
ul.disc{margin:9px 0 0;padding-left:17px}
ul.disc li{margin:6px 0;font-size:.89rem;line-height:1.55}
.panel{
  border:1px solid var(--line);border-radius:8px;padding:14px 16px;background:var(--head);
  margin:14px 0;
}
.panel h3{margin:0 0 8px;font-size:.95rem}
.panel ul{margin:.3em 0;padding-left:18px}
.panel li{margin:.3em 0;font-size:.87rem}
.imp{color:var(--red-fg);font-weight:600}
"""

GUIDE = """
<button class="guide" onclick="document.getElementById('guide').showModal()">How to read this report</button>
<dialog id="guide">
  <h3>How to read this report</h3>
  <p>Every reference that actually prints in the paper was checked against a live, authoritative
  source by a three-stage process. Nothing here is asserted without a link that was really fetched.</p>
  <ul>
    <li><b>Assistant</b> searched for each reference in a <i>closed</i> universe: the journal of
      record (or Crossref), the author&rsquo;s own site, or the official issuing institution.
      Blogs, ResearchGate and aggregators were off-limits. It was forbidden from inventing a link;
      when it found nothing, it said so.</li>
    <li><b>Associate</b> trusted none of that and clicked every link itself, confirming the page
      really is the work claimed &mdash; and corrected the Assistant where it was wrong.</li>
    <li><b>PI</b> spot-checked a sample personally, ruled on author order and currency, and wrote
      the notes you see.</li>
  </ul>
  <p><b>Nothing in your bibliography was changed.</b> This report tells you what is wrong; every
  decision remains yours. Where a working paper has since been published, that is reported as a
  choice for you &mdash; not applied &mdash; because changing a year rewrites your in-text citations.</p>
  <p><b>&ldquo;Publisher blocked the fetch&rdquo;</b> is not a failure. Many publishers refuse
  automated requests; those entries were confirmed at a second authoritative source, and we say so
  rather than pretending we loaded the page.</p>
  <p class="close"><button class="guide" onclick="document.getElementById('guide').close()">Close</button></p>
</dialog>
"""


# --------------------------------------------------------------------------------------------
# THE SUPER-RA MARK. Fixed. It goes on every report this pipeline will ever produce.
#
# This is a TOOL MARK, not a claim of authorship over the user's paper, and the distinction is
# load-bearing. A report generated by someone else, on someone else's bibliography, must credit
# super-RA for the method and Claude Code for the execution WITHOUT implying that super-RA's
# creator wrote their analysis. Naming the three roles separately is simply what is true:
#
#   super-RA        supplies the method
#   Claude Code     executes the run
#   the paper's author decides what to do about every finding
#
# Because the mark is fixed, there is nothing left to ask the user for, and nothing left to
# forget. The old version took `author` as a REQUIRED argument and died without it, which was
# the right fix for the wrong problem: the real failure was a byline with a hole in it, and a
# fixed mark cannot have one.
# --------------------------------------------------------------------------------------------
SUPER_RA_MARK = {
    "name": "super-RA",
    "creator": "Mamoor Ali Khan",
    "site": "https://mamooralikhan.com",
    "repo": "https://github.com/Mamooralikhan/super-RA",
}


def byline(n, refs_json, model):
    """The report is signed. The method is credited, and the use of AI is not hidden."""
    src = refs_json.get("source", {})
    m = SUPER_RA_MARK
    return (
        '<p class="byline">'
        f'Bibliography verification of <code>{e(src.get("tex", "the paper"))}</code> against '
        f'<code>{e(src.get("bib", "the bibliography"))}</code> &middot; '
        f'{n} references that actually print &middot; {date.today().isoformat()}<br>'
        f'Produced with <a href="{m["repo"]}"><b>{e(m["name"])}</b></a> <code>ref-check</code>, '
        f'a research-assistant skill library by '
        f'<a href="{m["site"]}">{e(m["creator"])}</a>. '
        f'Executed by <b>Claude Code</b> ({e(model)}), which fetches, checks, and reports.<br>'
        'super-RA reports; it never edits your <code>.tex</code> or <code>.bib</code>. '
        'The author of the paper remains the final verifier and makes every citation decision. '
        'The <code>.tex</code> and <code>.bib</code> were not modified.'
        '</p>'
        # THE READER MUST BE TOLD WHICH FORMAT THEY ARE LOOKING AT. If the report fell back to a
        # generic citation format, saying nothing would let the author assume these lines are how
        # their paper prints, and then read a formatting difference as a data error. Print it in
        # amber, above the table, where it cannot be missed.
        + (f'<p class="note" style="background:var(--amber-bg);border:1px solid var(--amber-line);'
           f'color:var(--amber-fg);padding:10px 12px;border-radius:6px;margin:0 0 18px">'
           f'{STYLE_NOTE}</p>' if STYLE_NOTE else ''))


def tiles(recs):
    n = len(recs)
    crit = sum(1 for r in recs if r["severity"] == "critical")
    major = sum(1 for r in recs if r["severity"] == "major")
    dec = sum(1 for r in recs if r["severity"] == "decision")
    ok = sum(1 for r in recs if r["final_status"] == "verified")
    niv = sum(1 for r in recs if r["final_status"] == "not_independently_verifiable")
    return f"""
<div class="tiles">
  <div class="tile"><div class="n">{n}</div><div class="l">references checked</div></div>
  <div class="tile crit"><div class="n">{crit}</div><div class="l">critical &mdash; wrong work</div></div>
  <div class="tile warn"><div class="n">{major}</div><div class="l">major &mdash; wrong metadata</div></div>
  <div class="tile warn"><div class="n">{dec}</div><div class="l">your call</div></div>
  <div class="tile ok"><div class="n">{ok}</div><div class="l">verified</div></div>
  <div class="tile"><div class="n">{niv}</div><div class="l">not independently verifiable</div></div>
</div>"""


def hygiene_panel(refs_json):
    """Facts about the .bib itself, COMPUTED from the data. Reported, never fixed.

    Everything here is derived. Do not hardcode a finding from one paper into this function:
    the panel must be true of whatever bibliography it is pointed at.

    The distinction that matters most is LATENT versus ACTIVE. A duplicate key whose first copy
    is missing a field is only a live bug if that key is actually cited, because BibTeX keeps the
    first copy. If it is not cited, it prints nothing and harms nothing today. Say so. Overstating
    a finding costs credibility on every other finding in the report.
    """
    h = refs_json["hygiene"]
    c = refs_json["counts"]
    cited = {r["key"] for r in refs_json["references"]}
    dups = h["duplicate_keys"]
    dup_cited = {k: n for k, n in dups.items() if k in cited}
    dup_uncited = {k: n for k, n in dups.items() if k not in cited}
    raw_entries = c["bib_unique_keys"] + sum(n - 1 for n in dups.values())

    items = []

    if dups:
        line = (f"<li><b>{len(dups)} duplicate keys</b> in the .bib "
                f"({c['bib_unique_keys']} unique keys across {raw_entries} raw entries). "
                f"BibTeX silently keeps the <i>first</i> copy and discards the rest, so if the "
                f"first copy is the less complete one, the bibliography renders the worse version.")
        if dup_cited:
            line += ("<br><b>These duplicates actually print:</b> "
                     + ", ".join(f"<code>{e(k)}</code>&times;{n}"
                                 for k, n in sorted(dup_cited.items())) + ".")
        if dup_uncited:
            line += (f"<br><span class='muted'>{len(dup_uncited)} further duplicated "
                     f"{'key is' if len(dup_uncited) == 1 else 'keys are'} never cited, so "
                     f"{'it does' if len(dup_uncited) == 1 else 'they do'} no harm today. "
                     f"Latent, not active: a trap for a future draft.</span>")
        items.append(line + "</li>")

    missing = [r for r in refs_json["references"] if r.get("missing_required_fields")]
    if missing:
        items.append(
            f"<li><b>{len(missing)} printing entries are missing a required field</b> for their "
            f"type: "
            + ", ".join(f"<code>{e(r['key'])}</code> "
                        f"({e(', '.join(r['missing_required_fields']))})" for r in missing[:8])
            + (f" and {len(missing) - 8} more." if len(missing) > 8 else ".")
            + "</li>")

    items.append(
        f"<li><b>{c['bib_uncited']} of the {c['bib_unique_keys']} entries in the .bib are never "
        f"cited.</b> They never print, and they were <b>not</b> verified. Only the "
        f"{c['cited_unique']} that reach the page were.</li>")

    ts = refs_json["tex_structure"]
    appx_only = c.get("appendix_only", 0)
    if c.get("cited_in_appendix"):
        if appx_only:
            appx = (f"The appendix (from line {ts['appendix_starts_line']}) cites "
                    f"{c['cited_in_appendix']} references, of which <b>{appx_only} appear only "
                    f"there</b> and not in the body.")
        else:
            appx = (f"The appendix (from line {ts['appendix_starts_line']}) cites "
                    f"{c['cited_in_appendix']} references, and <b>every one is already cited in "
                    f"the body</b>, so the appendix introduces no new references.")
        items.append(f"<li>{appx}</li>")

    if ts.get("dead_lines_after_end_document"):
        items.append(
            f"<li>The {ts['dead_lines_after_end_document']} lines after "
            f"<code>\\end{{document}}</code> were excluded, because nothing there compiles or "
            f"prints. Citations parked in that dead zone are not part of your bibliography.</li>")

    if refs_json.get("nocite_all"):
        items.append("<li><code>\\nocite{*}</code> is present, so <b>every</b> .bib entry prints "
                     "and all of them were checked.</li>")

    return ('<div class="panel"><h3>Bibliography hygiene: reported, not fixed</h3><ul>'
            + "".join(items) + "</ul></div>")


def page(title, body, favicon_note=""):
    return f"""<title>{e(title)}</title>
<style>{CSS}</style>
<div class="wrap">
{body}
</div>"""


# --------------------------------------------------------------------------------------------
# Report 1: the audit trail. Four columns, one row per reference, every claim carrying its link.
# --------------------------------------------------------------------------------------------
def render_audit(recs, refs_json, model):
    rows = []
    for r in sorted(recs, key=lambda x: ({"critical": 0, "major": 1, "decision": 2,
                                          "minor": 3, "clean": 4}[x["severity"]], x["key"])):
        a = r["assistant"]
        sev = r["severity"]
        cls = "red" if sev == "critical" else ("amber" if sev in ("major", "decision") else "green")
        vm = r.get("verified_metadata") or {}

        disc = r.get("bib_discrepancies") or []
        disc_html = ("<ul class='disc'>"
                     + "".join(f"<li>{e(d)}</li>" for d in disc[:6])
                     + (f"<li class='muted'>+{len(disc)-6} more</li>" if len(disc) > 6 else "")
                     + "</ul>") if disc else "<p class='muted note'>No discrepancy found.</p>"

        corr = r.get("corrections_made") or []
        corr_html = ("<p class='note'><b>Corrected the Assistant:</b></p><ul class='disc'>"
                     + "".join(f"<li>{e(x)}</li>" for x in corr) + "</ul>") if corr else ""

        spot = ("<p class='note'><b>PI spot-checked this personally:</b> "
                f"{e(r['pi_spot_check_note'])}</p>") if r.get("pi_spot_checked") else ""

        rows.append(f"""
<tr class="{cls}">
  <td>
    <span class="key">{e(r['key'])}</span>
    <p class="note">{STYLED.get(r['key'], {}).get('original') or cite_from_bib(r['bib_fields'])}</p>
    <p class="note muted">@{e(r['entry_type'])} &middot; cited {r['cite_count']}&times;
       in {e(', '.join(r['cited_in']))}</p>
  </td>
  <td>
    <p class="note muted">searched: {e(', '.join(a.get('searched_where') or []) or a.get('source_universe_used',''))}</p>
    <p class="note">{link(a.get('primary_link'))}</p>
    <p class="note">{e(a.get('fetch_note',''))[:400]}</p>
  </td>
  <td>
    <p class="note"><b>{e(LINK_LABEL.get(r['link_status'], r['link_status']))}</b></p>
    {f"<p class='note muted'>corroborated at {link(r.get('corroborating_source'))}</p>" if r['link_status']=='blocked_corroborated' else ""}
    {corr_html}
    <p class="note">{e(r.get('associate_note',''))[:300]}</p>
  </td>
  <td>
    <span class="badge b-{sev}">{e(SEV_LABEL[sev])}</span>
    <span class="badge">{e(STATUS_LABEL[r['final_status']])}</span>
    <p class="note">{e(r['pi_note'])}</p>
    {spot}
    {disc_html}
  </td>
</tr>""")

    body = f"""
<h1>Bibliography verification &mdash; audit trail</h1>
{byline(len(recs), refs_json, model)}
{GUIDE}
{tiles(recs)}
<p class="muted" style="font-size:.85rem">Sorted by severity. Every link below was fetched by a
machine that was forbidden from inventing one; where nothing was found, the report says so.</p>
{hygiene_panel(refs_json)}
<div class="tablewrap">
<table>
  <colgroup>
    <col style="width:24%"><col style="width:22%"><col style="width:22%"><col style="width:32%">
  </colgroup>
  <thead><tr>
    <th>Original (your .bib)</th>
    <th>Assistant &mdash; what it found</th>
    <th>Associate &mdash; clicked the link</th>
    <th>PI &mdash; ruling</th>
  </tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
</div>
"""
    return page("Bibliography verification ,  audit trail", body)


# --------------------------------------------------------------------------------------------
# Report 2: the red/green comparison. Changed rows red, clean rows green.
# CHANGED IS DECIDED ON THE RENDERED STRINGS, not on proxy metadata fields.
# --------------------------------------------------------------------------------------------
def render_comparison(recs, refs_json, model):
    rows = []
    order = {"critical": 0, "major": 1, "decision": 2, "minor": 3, "clean": 4}
    for r in sorted(recs, key=lambda x: (order[x["severity"]], x["key"])):
        sev = r["severity"]
        st = STYLED.get(r["key"], {})
        original = st.get("original") or cite_from_bib(r["bib_fields"])
        corrected = st.get("corrected") or cite_from_verified(r.get("verified_metadata"))

        needs = r["final_status"] in ("needs_author_review", "not_found")
        cls = "red" if needs else ("amber" if r["final_status"] == "not_independently_verifiable"
                                   else "green")

        if r["final_status"] == "not_found" or r["link_status"] == "mismatch":
            corrected_cell = ('<p class="imp">The cited work could not be found at any '
                              'authoritative source.</p>'
                              '<p class="note muted">Reported as not found rather than replaced '
                              'with a guess.</p>')
        elif not corrected:
            corrected_cell = '<p class="muted">&mdash;</p>'
        else:
            same = corrected.strip() == original.strip()
            corrected_cell = (f'<p class="note">{corrected}</p>'
                              + ('<p class="note muted">Identical to your entry.</p>' if same else ''))
            if r.get("verified_metadata", {}).get("doi"):
                corrected_cell += (f'<p class="note">{link("https://doi.org/" + r["verified_metadata"]["doi"], "doi.org/" + r["verified_metadata"]["doi"])}</p>')

        disc = r.get("bib_discrepancies") or []
        extra = ("<ul class='disc'>" + "".join(f"<li>{e(d)}</li>" for d in disc[:4])
                 + (f"<li class='muted'>+{len(disc)-4} more &mdash; see the audit trail</li>"
                    if len(disc) > 4 else "") + "</ul>") if disc else ""

        rows.append(f"""
<tr class="{cls}">
  <td>
    <span class="key">{e(r['key'])}</span>
    <p class="note">{original}</p>
  </td>
  <td>{corrected_cell}</td>
  <td>
    <span class="badge b-{sev}">{e(SEV_LABEL[sev])}</span>
    <p class="note">{e(r['pi_note'])}</p>
    {extra}
  </td>
</tr>""")

    changed = sum(1 for r in recs if r["final_status"] in ("needs_author_review", "not_found"))
    body = f"""
<h1>Bibliography verification &mdash; what needs changing</h1>
{byline(len(recs), refs_json, model)}
{GUIDE}
{tiles(recs)}
<p class="muted" style="font-size:.85rem">
<b>Red</b> = needs your attention. <b>Amber</b> = real, but not confirmable at an authoritative
source (not an error). <b>Green</b> = confirmed correct; any notes are cosmetic.
{changed} of {len(recs)} references need a decision from you. Sorted by severity.</p>
{hygiene_panel(refs_json)}
<div class="tablewrap">
<table>
  <colgroup><col style="width:30%"><col style="width:32%"><col style="width:38%"></colgroup>
  <thead><tr>
    <th>Original &mdash; as your .bib has it</th>
    <th>Corrected &mdash; as the source has it</th>
    <th>Explanation</th>
  </tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
</div>
"""
    return page("Bibliography verification ,  what needs changing", body)


def main():
    ap = argparse.ArgumentParser(description="Render the two HTML reports from one JSON.")
    # No --author. The byline is the fixed super-RA mark (see SUPER_RA_MARK above), so there is
    # nothing to ask for and nothing to forget. It credits the METHOD, not the user's paper.
    ap.add_argument("--model", default="Claude Opus 4.8",
                    help="The Claude model that executed the run. Disclosed on the byline.")
    ap.add_argument("--style", default=None,
                    help="Override the bibliography style. Use this when the paper is biblatex, "
                         "or declares a .bst you do not have, and step 01's preflight told the "
                         "user so. Re-running step 06 with this flag costs nothing: no reference "
                         "is re-fetched.")
    ap.add_argument("--pi", default="bib_verification/data/05_pi_review.json")
    ap.add_argument("--refs", default="bib_verification/data/01_references.json")
    ap.add_argument("--outdir", default="reports")
    args = ap.parse_args()

    PI = Path(args.pi)
    REFS = Path(args.refs)
    OUT_AUDIT = Path(args.outdir) / "bibliography_audit.html"
    OUT_COMPARE = Path(args.outdir) / "bibliography_comparison.html"

    pi = json.loads(PI.read_text(encoding="utf-8"))
    refs_json = json.loads(REFS.read_text(encoding="utf-8"))
    recs = pi["references"]

    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    # Render every citation through the paper's OWN .bst, so the author reads their references
    # in the format their paper actually prints. Falls back to the generic format, out loud.
    global STYLED, STYLE_NOTE
    src = refs_json.get("source", {})
    # --style beats the paper, because the user has been TOLD what the paper says and has
    # chosen otherwise. Step 01's preflight is what gave them that choice, before the tiers ran.
    style = args.style or src.get("bibliography_style")
    engine = "bibtex" if args.style else src.get("bibliography_engine", "bibtex")
    tex_dir = str(Path(src.get("tex", ".")).resolve().parent)
    # TWO SEPARATE BibTeX RUNS, one per column. A style file formats each entry in the light of
    # its neighbours, so a reference sitting next to its own corrected twin gets its author
    # suppressed by \bysame (rendering as ",, and ,") and its year suffixed to "2016a". Keeping
    # the columns in separate runs makes that impossible rather than merely unlikely.
    originals, correcteds = {}, {}
    for r in recs:
        originals[r["key"]] = bibtex_from_bib(
            r["key"], r.get("entry_type"), r.get("bib_fields"))
        cb = bibtex_from_verified(r["key"], r.get("entry_type"), r.get("verified_metadata"))
        if cb:
            correcteds[r["key"]] = cb

    pre = bst_render.preflight(style, [tex_dir, "."], engine)
    if not pre["can_render"]:
        bst_render.report_preflight(pre)

    rendered, STYLE_NOTE = (
        bst_render.render_pair(originals, correcteds, style, [tex_dir, "."])
        if pre["can_render"] else (None, pre["reason"]))
    if rendered:
        STYLED.update(rendered)
        n = sum(1 for v in rendered.values() if v.get("original"))
        print(f"  style: rendered {n} references through the paper's own {style}.bst "
              f"(each formatted alone, so no entry borrows or suppresses a neighbour's author)")
    else:
        print(f"  style: {re.sub(r'<[^>]+>', '', STYLE_NOTE)}")

    OUT_AUDIT.write_text(render_audit(recs, refs_json, args.model), encoding="utf-8")
    OUT_COMPARE.write_text(
        render_comparison(recs, refs_json, args.model), encoding="utf-8")

    # "Report, do not fix" is a claim, so verify it instead of asserting it. 01 recorded the byte
    # sizes of the .tex and .bib at extraction time; if either moved, the pipeline touched a file
    # it had no business touching, and the user needs to know before they trust anything here.
    src = refs_json.get("source", {})

    # source_files covers EVERY file step 01 read: the main .tex, each \input child, and each
    # .bib. Checking only the main .tex, as an earlier version did, would have missed a write to
    # sections/intro.tex entirely.
    files = src.get("source_files")
    if not files:  # a 01_references.json written before source_files existed
        files = [{"path": src.get(k), "bytes": src.get(b), "role": r}
                 for k, b, r in (("tex", "tex_bytes", "tex_main"), ("bib", "bib_bytes", "bib"))]

    checked = touched = 0
    for f in files:
        p, expected = f.get("path"), f.get("bytes")
        if not p or expected is None or not Path(p).is_file():
            continue
        checked += 1
        actual = Path(p).stat().st_size
        if actual != expected:
            touched += 1
            print(f"  source {f.get('role','file')}: {p}  CHANGED ({expected} -> {actual})")

    if touched:
        print(f"  WARNING: {touched} of {checked} source files were MODIFIED during the run. "
              "This pipeline must never write to the paper or the bibliography. Do not trust "
              "this report until you know what wrote to them.")
    else:
        print(f"  source integrity: all {checked} source files unchanged "
              "(main .tex, every \\input child, and every .bib).")

    print(f"\nWrote {OUT_AUDIT}")
    print(f"Wrote {OUT_COMPARE}")
    print(f"\n  {len(recs)} references rendered from a single source of truth "
          f"(05_pi_review.json), so the two reports cannot disagree.")


if __name__ == "__main__":
    main()
