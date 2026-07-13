#!/usr/bin/env python3
"""
STEP 01 of the ref-check pipeline. See 00_README.md for run order.

Usage:  python3 01_extract_citations.py --tex <paper>.tex --bib <bibliography>.bib [more.bib ...]

Consumes : the paper .tex, every file it \input's, and its .bib files
           (READ-ONLY. Never written to. Not by any step.)
Produces : bib_verification/data/01_references.json

Builds the list of references that ACTUALLY PRINT, and attaches to each the "already known to
be shaky" flags that tell the Assistant tier where to work hardest.

Why the printed set is not simply "every entry in the .bib":
  With natbib or BibTeX and no \\nocite{*}, only keys reached by a \\cite-family command are
  typeset. A .bib usually holds many more entries than the paper cites. On the paper this
  pipeline was built against, the .bib had 175 unique entries and the paper cited 66. Verifying
  the other 109 would have been 2.5x the work for zero effect on the submitted document.

READ references/extraction-rules.md BEFORE CHANGING ANYTHING HERE. Every guard in this file
exists because breaking it produced a FALSE ACCUSATION against a bibliography that was correct.
A bad extractor does not fail loudly; it invents a defect and the whole pipeline then earnestly
investigates a problem that never existed.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

# Anything at or beyond the current year cannot be a settled published record.
FORWARD_DATED_FROM = date.today().year

# --------------------------------------------------------------------------------------------
# RULE 10. FIND EVERY CITATION COMMAND, INCLUDING THE ONES WE HAVE NEVER HEARD OF.
#
# The old regex named eight natbib commands. It therefore could not see:
#   - \Citep, \Citet, \Citeauthor        natbib's CAPITALISED sentence-start forms
#   - \parencite, \textcite, \autocite,  ALL of biblatex
#     \footcite, \supercite, \fullcite
#   - \citeA, \shortcite, \citeN         apacite
#   - \nocite{key}                       which DOES print that entry
#
# 14 of 24 real citation commands were invisible. A paper mixing \citep with \textcite lost every
# \textcite silently: no error, and Rule 7's "cited but missing from .bib" assertion cannot catch
# it either, because a citation the parser never saw cannot be reported as missing. It is the
# same silent under-count as Rule 8, arriving through a different door.
#
# THE FIX IS NOT A LONGER LIST. Enumerating every command every package will ever ship is a game
# we lose on the next release. So: match ANY macro whose name contains "cite", take its keys, and
# NAME the ones we do not recognise. Missing a citation command is now structurally impossible;
# the worst case is that we over-collect, and Rule 7 catches that loudly by finding a "key" that
# is not in the .bib. Over-collecting fails noisily. Under-collecting fails silently. Given the
# choice, always take the noisy one.
# --------------------------------------------------------------------------------------------

# Everything we know about. Anything cite-like NOT in here is still collected, and reported.
KNOWN_CITE_COMMANDS = {
    # natbib
    "cite", "citep", "citet", "citealp", "citealt", "citeauthor", "citeyear", "citeyearpar",
    "citefullauthor", "citenum", "citetext",
    "Cite", "Citep", "Citet", "Citealp", "Citealt", "Citeauthor", "Citeyear", "Citeyearpar",
    # biblatex
    "parencite", "Parencite", "textcite", "Textcite", "autocite", "Autocite",
    "footcite", "footcitetext", "smartcite", "Smartcite", "supercite",
    "fullcite", "footfullcite", "citetitle", "citedate", "citeurl", "Citeauthors",
    # biblatex multi-key forms: \cites{a}{b}{c}
    "cites", "parencites", "Parencites", "textcites", "Textcites",
    "autocites", "Autocites", "supercites", "footcites", "smartcites",
    # apacite
    "citeA", "citeNP", "citeN", "shortcite", "shortciteA", "shortciteNP", "citeyearNP",
    # \nocite{key} prints that entry. \nocite{*} is handled separately, as a scope change.
    "nocite",
}

# The plural forms take a RUN of brace groups: \cites{a}{b}{c}. Everything else takes exactly one,
# or we would swallow the next brace group in the prose: "\citet{smith} {and others}".
MULTI_KEY_COMMANDS = {c for c in KNOWN_CITE_COMMANDS if c.lower().endswith("cites")}

# Any macro whose name contains "cite", with optional star and any number of [optional] args,
# stopping at the opening brace of its first argument.
ANY_CITE_RE = re.compile(r"\\([A-Za-z@]*[Cc]ite[A-Za-z@]*)\s*\*?\s*(?:\[[^\]]*\])*\s*(?=\{)")
ENTRY_START_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,")

# \input{sections/intro}, \include{sections/intro}, \subfile{sections/intro}
CHILD_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]*)\}")

# The real \appendix, and NOT \appendixwithtoc, \appendixname, or any other macro that merely
# begins with those letters. The word boundary is the whole point of using a regex here.
APPENDIX_RE = re.compile(r"\\appendix(?![A-Za-z@])")

# A child pulled in by \subfile carries its own preamble and \begin{document}. Only the matter
# between \begin{document} and \end{document} is really typeset into the parent.
DOC_BEGIN = "\\begin{document}"
DOC_END = "\\end{document}"

MAX_INPUT_DEPTH = 20

# Fields BibTeX/AER needs for a complete entry of each type.
REQUIRED_FIELDS = {
    "article": ["author", "title", "journal", "year", "volume", "pages"],
    "book": ["author", "title", "publisher", "year"],
    "inbook": ["author", "title", "publisher", "year"],
    "incollection": ["author", "title", "booktitle", "publisher", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "unpublished": ["author", "title", "year"],
    "misc": ["author", "title", "year"],
    "online": ["title", "year"],
    "dataset": ["title", "year"],
}

# An author string containing one of these is an organisation, not a person. The PI tier must
# not let such an entry be silently reattributed to an individual staff member.
INSTITUTIONAL_MARKERS = [
    "world bank", "government", "ministry", "commission", "bureau", "agency", "nasa",
    "noaa", "who", "united nations", "oecd", "institute", "centre", "center", "council",
    "department", "national", "crea", "copernicus", "ipcc", "usaid", "unicef",
]


def strip_tex_comments(lines):
    """Drop everything after an unescaped % on each line. \\% is a literal percent, not a comment."""
    out = []
    for line in lines:
        m = re.match(r"^(.*?)(?<!\\)%", line)
        out.append(m.group(1) if m else line)
    return out


def _brace_group(text, i):
    """Read one balanced {...} starting at text[i] == '{'. Returns (contents, index_after)."""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1: j], j + 1
    return None, len(text)  # unbalanced; give up on this one rather than guessing


def scan_citations(text):
    """Rule 10. Every citation key in a chunk of TeX, plus every cite-like command we met.

    Returns (keys_in_order_with_duplicates, {command: occurrences}).

    Brace-aware, not regex-aware, because a key list is a brace group and BibTeX keys are allowed
    to be strange. `\\nocite{*}` contributes no key: it is a change of SCOPE, handled by the
    caller, not a citation of a work called "*".
    """
    keys, commands = [], Counter()
    for m in ANY_CITE_RE.finditer(text):
        name = m.group(1)
        commands[name] += 1

        # Walk the brace groups. Only the plural "cites" forms take a run of them.
        i = m.end()
        groups = 0
        while i < len(text) and text[i] == "{":
            body, i = _brace_group(text, i)
            if body is None:
                break
            for k in body.split(","):
                k = k.strip()
                if k and k != "*":
                    keys.append(k)
            groups += 1
            if name not in MULTI_KEY_COMMANDS or groups > 20:
                break
    return keys, commands


def keys_in(text):
    """All citation keys appearing in a chunk of TeX, in order, with duplicates."""
    return scan_citations(text)[0]


def unknown_cite_commands(text):
    """Cite-like commands we do not have on the list. Never silently dropped; always reported."""
    _, commands = scan_citations(text)
    return {c: n for c, n in commands.items() if c not in KNOWN_CITE_COMMANDS}


def resolve_child(name, main_dir):
    """Locate the file behind an \\input{name}, the way TeX would.

    TeX resolves a child path relative to the directory of the MAIN document, not relative to
    whichever file did the \\input-ing. A grandchild therefore resolves against main_dir too.
    The .tex extension is optional in TeX and usually omitted.
    """
    name = name.strip()
    if not name:
        return None
    for candidate in (main_dir / name, main_dir / (name + ".tex")):
        if candidate.is_file():
            return candidate.resolve()
    return None


def expand_children(text, main_dir, visited, files_read, unresolved, depth=0):
    """Rule 8. Splice every \\input / \\include / \\subfile child into the text, recursively.

    WITHOUT THIS, A MULTI-FILE PAPER IS SILENTLY UNDER-CHECKED. A paper split across
    sections/*.tex keeps its citations in the children. An extractor that reads only the main
    file does not error and does not warn: it simply reports fewer references, and every
    assertion below still passes, because a citation the parser never saw cannot be flagged as
    missing from the .bib. The run looks clean. Half the paper was never checked.

    ORDER IS LOAD-BEARING, AND IT IS NOT THE OBVIOUS ONE.

    Rule 2 (truncate at \\end{document}) and Rule 3 (strip comments) BOTH run before this
    function is ever called, and both must. The reference paper proves why:

      - It \\input's ~15 table files AFTER \\end{document}. Expanding the dead zone would drag
        them back in through the side door, defeating Rule 2 entirely.
      - It contains three COMMENTED-OUT \\input lines whose targets do not exist on disk
        (main.tex lines 149, 980, 1041). Resolving children before stripping comments would
        halt the pipeline on three files that TeX itself never reads. That is a false failure,
        which is the precise disease every guard in this file exists to cure.

    An unresolved child is never guessed at. It is collected and the caller halts, because an
    \\input pointing at a file that is not there means an unknown number of unchecked citations,
    and this pipeline does not proceed on an unknown.
    """
    if depth > MAX_INPUT_DEPTH:
        sys.exit(f"FATAL: \\input nesting deeper than {MAX_INPUT_DEPTH}. Suspect a cycle.")

    def splice(match):
        child = resolve_child(match.group(1), main_dir)
        if child is None:
            unresolved.append(match.group(1).strip())
            return ""
        if child in visited:
            return ""  # already spliced in, or a cycle. Either way, do not read it twice.
        visited.add(child)

        body = "\n".join(strip_tex_comments(child.read_text(encoding="utf-8").split("\n")))

        # A \subfile child is a compilable document in its own right. Only what sits between
        # \begin{document} and \end{document} is typeset into the parent; its preamble is not.
        start = body.find(DOC_BEGIN)
        if start != -1:
            stop = body.find(DOC_END, start)
            body = body[start + len(DOC_BEGIN): stop if stop != -1 else len(body)]

        files_read.append({
            "path": str(child),
            "bytes": child.stat().st_size,
            "role": "tex_child",
            "citations": len(keys_in(body)),
        })
        return expand_children(body, main_dir, visited, files_read, unresolved, depth + 1)

    return CHILD_RE.sub(splice, text)


def parse_fields(chunk):
    """Brace-aware field parser for one .bib entry.

    Do NOT anchor fields to line-start. BibTeX does not care about newlines, and this file
    contains at least one entry (Fearon_1999) written entirely on a single line. A line-anchored
    regex extracts ZERO fields from such an entry, which then looks like an empty stub and gets
    reported as unfindable -- a false defect invented by the parser, not present in the data.

    Instead: walk the entry body, tracking brace depth and quote state, and split on commas that
    sit at depth 0. That is what BibTeX itself does.
    """
    open_brace = chunk.find("{")
    if open_brace == -1:
        return {}
    depth, end = 0, len(chunk)
    for i in range(open_brace, len(chunk)):
        if chunk[i] == "{":
            depth += 1
        elif chunk[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    body = chunk[open_brace + 1:end]

    # Drop the citation key: everything up to the first top-level comma.
    parts, depth, cur, in_quote = [], 0, [], False
    for ch in body:
        if ch == '"' and depth == 0:
            in_quote = not in_quote
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0 and not in_quote:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))

    fields = {}
    for part in parts[1:]:  # parts[0] is the citation key
        if "=" not in part:
            continue
        name, _, val = part.partition("=")
        name = name.strip().lower()
        if not re.fullmatch(r"\w+", name):
            continue
        val = val.strip().rstrip(",").strip()
        if (val.startswith("{") and val.endswith("}")) or (val.startswith('"') and val.endswith('"')):
            val = val[1:-1]
        fields[name] = re.sub(r"\s+", " ", val).strip()
    return fields


def parse_bib(raw):
    """Parse .bib first-wins, mirroring BibTeX's own duplicate-key behaviour.

    Returns (first_wins, duplicate_counts) where first_wins maps key -> {type, raw, fields}.
    """
    first_wins = {}
    counts = Counter()
    # Split at each line whose first non-space character is @. The leading [ \t]* is load-bearing.
    # A .bib entry may be INDENTED before its @, and BibTeX accepts that. Splitting on a bare
    # "\n@" silently swallows such an entry into its predecessor and merges the two field sets,
    # which CORRUPTS the predecessor rather than merely losing a key. This happened for real:
    # a perfectly good entry had a neighbour's fields grafted onto it and nobody noticed until
    # the unique-key count came out one short. See extraction-rules.md, Rule 6.
    for chunk in re.split(r"\n(?=[ \t]*@)", raw):
        m = ENTRY_START_RE.match(chunk.strip())
        if not m:
            continue
        etype, key = m.group(1).lower(), m.group(2).strip()
        counts[key] += 1
        if key in first_wins:
            continue  # BibTeX ignores later copies. So do we.
        fields = parse_fields(chunk.strip())
        first_wins[key] = {"entry_type": etype, "raw_bibtex": chunk.strip(), "fields": fields}
    return first_wins, counts


def compute_flags(key, entry, dup_count):
    """The pipeline's own 'this one is already known to be shaky' signals.

    A .bib has no editorial comments the way a Word bibliography does, so the pipeline computes
    its own work items. These are passed to the Assistant tier as context -- as things to
    RESOLVE, not as instructions to blindly overwrite the author's choices.
    """
    flags = []
    etype = entry["entry_type"]
    fields = entry["fields"]

    if dup_count > 1:
        flags.append("duplicate_key")

    missing = [f for f in REQUIRED_FIELDS.get(etype, ["author", "title", "year"]) if f not in fields]
    if missing:
        flags.append("missing_required_fields")

    if "doi" not in fields:
        flags.append("no_doi")

    year_m = re.search(r"(\d{4})", fields.get("year", ""))
    year = int(year_m.group(1)) if year_m else None
    if year and year >= FORWARD_DATED_FROM:
        flags.append("forward_dated")

    author = fields.get("author", "").lower()
    if author and any(marker in author for marker in INSTITUTIONAL_MARKERS):
        flags.append("institutional_author")

    # A stub is an entry so empty it cannot be checked against anything.
    core_present = sum(1 for f in ("author", "title", "year") if fields.get(f))
    if core_present <= 1:
        flags.append("stub_entry")

    return flags, missing, year


def main():
    ap = argparse.ArgumentParser(description="Extract the references that actually print.")
    ap.add_argument("--tex", required=True, help="the MAIN paper .tex (the one with \\begin{document})")
    ap.add_argument("--bib", required=True, nargs="+",
                    help="the .bib bibliography. Repeatable: a paper may load several.")
    ap.add_argument("--out", default="bib_verification/data/01_references.json")
    args = ap.parse_args()

    tex_path = Path(args.tex)
    bib_paths = [Path(b) for b in args.bib]
    out_path = Path(args.out)
    for p in [tex_path] + bib_paths:
        if not p.is_file():
            sys.exit(f"FATAL: no such file: {p}")

    main_dir = tex_path.resolve().parent
    lines = tex_path.read_text(encoding="utf-8").split("\n")

    # --- The guards run in this order, and the order is not interchangeable. --------------------
    # Rule 2 first: truncate at \end{document}. The reference paper \input's ~15 table files AFTER
    #               it. Expanding before truncating would drag the dead zone back in.
    # Rule 3 next : strip comments. The same paper has three commented-out \input lines whose
    #               targets do not exist. Resolving before stripping would halt on files TeX never
    #               reads.
    # Rule 8 last : only now, splice in the children.
    try:
        end_idx = next(i for i, l in enumerate(lines) if l.strip().startswith("\\end{document}"))
    except StopIteration:
        sys.exit(f"FATAL: no \\end{{document}} found in {tex_path}")

    # Rule 9. Find \begin{document} FIRST, and look for \appendix only after it.
    #
    # THE OBVIOUS IMPLEMENTATION, "the first line starting with \appendix", IS WRONG, AND IT
    # FAILS SILENTLY. Papers define appendix macros in the preamble:
    #
    #     \newcommand*\appendixwithtoc{%
    #       \appendix                      <- the naive scan stops HERE, in the preamble
    #       ...}
    #     \begin{document}
    #     ...
    #     \appendix                        <- the real one, hundreds of lines later
    #
    # The naive scan then calls the preamble "the body" (which cites nothing) and the entire
    # document "the appendix". It does not crash. On a real paper it reported all 35 references
    # as appendix-only and zero in the body, confidently and in a clean table.
    #
    # Two conditions, and both are needed:
    #   1. the \appendix must come after \begin{document}, which excludes preamble macro bodies;
    #   2. \b word boundary, or "\appendixwithtoc" matches the prefix "\appendix" and we are
    #      back where we started.
    try:
        begin_idx = next(
            i for i, l in enumerate(lines) if l.strip().startswith("\\begin{document}"))
    except StopIteration:
        sys.exit(f"FATAL: no \\begin{{document}} found in {tex_path}. Is this the MAIN .tex?")
    if begin_idx > end_idx:
        sys.exit(f"FATAL: \\begin{{document}} comes after \\end{{document}} in {tex_path}.")

    app_idx = next(
        (i for i in range(begin_idx + 1, end_idx + 1)
         if APPENDIX_RE.match(lines[i].strip())),
        end_idx,
    )

    live = strip_tex_comments(lines[: end_idx + 1])
    dead_text = "\n".join(strip_tex_comments(lines[end_idx + 1:]))

    files_read = [{
        "path": str(tex_path),
        "bytes": tex_path.stat().st_size,
        "role": "tex_main",
        "citations": len(keys_in("\n".join(live))),
    }]
    visited, unresolved = {tex_path.resolve()}, []

    # The body starts at \begin{document}. Nothing in the preamble is typeset.
    body_text = expand_children(
        "\n".join(live[begin_idx:app_idx]), main_dir, visited, files_read, unresolved)
    appx_text = expand_children(
        "\n".join(live[app_idx:]), main_dir, visited, files_read, unresolved)

    # Rule 8's assertion. An \input we could not find is an unknown number of unchecked citations.
    # Guessing is the one thing this pipeline is built never to do.
    if unresolved:
        sys.exit(
            "FATAL: these \\input/\\include targets do not exist on disk:\n  "
            + "\n  ".join(sorted(set(unresolved)))
            + f"\n\nResolved relative to {main_dir}. Each one is an unknown number of citations "
              "that would go unchecked. Fix the path, or comment the line out if it is dead."
        )

    # Rule 1. \nocite{*} means EVERY entry prints, and the scope of the whole job changes. It may
    # sit in a child, so this is checked only after the children are spliced in.
    nocite_all = bool(re.search(r"\\nocite\s*\{\s*\*\s*\}", body_text + "\n" + appx_text))

    # The paper's OWN bibliography style. Step 06 renders the report through this exact .bst, so
    # the author sees their references in the format their paper actually prints, not in some
    # house format we invented. Read it from the paper; never assume one.
    live_all = "\n".join(strip_tex_comments(lines[: end_idx + 1]))
    style_m = re.search(r"\\bibliographystyle\s*\{([^}]*)\}", live_all)
    bib_style = style_m.group(1).strip() if style_m else None

    # biblatex has NO \bibliographystyle. It is configured in the package options and driven by
    # biber, so a missing style line does not mean the paper is styleless: it means we are looking
    # for the wrong thing. Detect it explicitly rather than silently reporting "no style found".
    engine = "bibtex"
    if re.search(r"\\usepackage(?:\[[^\]]*\])?\s*\{[^}]*biblatex[^}]*\}", live_all) \
            or re.search(r"\\addbibresource\s*\{", live_all) \
            or re.search(r"\\printbibliography", live_all):
        engine = "biblatex"
        bl = re.search(r"\\usepackage\[([^\]]*)\]\s*\{[^}]*biblatex", live_all)
        if bl:
            opt = re.search(r"\bstyle\s*=\s*([\w-]+)", bl.group(1))
            if opt:
                bib_style = bib_style or opt.group(1)

    body_keys, body_cmds = scan_citations(body_text)
    appx_keys, appx_cmds = scan_citations(appx_text)
    all_live = body_keys + appx_keys
    cited = sorted(set(all_live))

    # Rule 10. The census of citation commands this paper actually uses, and the ones we did not
    # recognise. An unrecognised command is NOT dropped: its keys are already in `cited` above.
    # It is surfaced so a human can confirm it really is a citation command, because the one thing
    # we will not do is quietly verify fewer references than the paper prints.
    cite_commands = body_cmds + appx_cmds
    unknown_cmds = {c: n for c, n in cite_commands.items() if c not in KNOWN_CITE_COMMANDS}

    # Rule 4, extended across files. BibTeX reads several .bib files in the order given and the
    # FIRST definition of a key wins, exactly as it does within a single file.
    bib, dup_counts = {}, Counter()
    for bp in bib_paths:
        entries, counts = parse_bib(bp.read_text(encoding="utf-8"))
        dup_counts.update(counts)
        for k, v in entries.items():
            bib.setdefault(k, v)
        files_read.append({
            "path": str(bp), "bytes": bp.stat().st_size, "role": "bib", "citations": None,
        })

    # \nocite{*} means every entry prints, so the scope is the whole file, not just cited keys.
    if nocite_all:
        cited = sorted(set(cited) | set(bib))

    # --- Assertions. A failure here means the reference list would be wrong. Stop, do not guess.
    missing_from_bib = [k for k in cited if k not in bib]
    if missing_from_bib:
        sys.exit(f"FATAL: cited but absent from the .bib: {missing_from_bib}")

    dead_only = sorted(set(keys_in(dead_text)) - set(cited))

    records = []
    for key in cited:
        entry = bib[key]
        flags, missing, year = compute_flags(key, entry, dup_counts[key])
        where = []
        if key in set(body_keys):
            where.append("body")
        if key in set(appx_keys):
            where.append("appendix")
        records.append({
            "key": key,
            "entry_type": entry["entry_type"],
            "cited_in": where,
            "cite_count": all_live.count(key),
            "raw_bibtex": entry["raw_bibtex"],
            "raw_fields": entry["fields"],
            "year": year,
            "entry_flags": flags,
            "missing_required_fields": missing,
            "bib_duplicate_copies": dup_counts[key],
        })

    payload = {
        "source": {
            "tex": str(tex_path),
            "bib": ", ".join(str(b) for b in bib_paths),
            # Byte sizes at extraction time. The final report re-checks these to PROVE the
            # pipeline did not touch the user's files. "Report, do not fix" is a claim we verify.
            #
            # source_files covers EVERY file read, including each \input child. The old schema
            # could only vouch for the main .tex, so a pipeline that wrote to sections/intro.tex
            # would have gone unnoticed. Now nothing that is read escapes the integrity check.
            "source_files": files_read,
            "tex_bytes": tex_path.stat().st_size,
            "bib_bytes": sum(b.stat().st_size for b in bib_paths),
            # e.g. "aer", "apsr", "chicago", "plainnat". Step 06 renders through this real .bst.
            "bibliography_style": bib_style,
            "bibliography_engine": engine,     # "bibtex" or "biblatex"
        },
        "nocite_all": nocite_all,
        "note": "READ-ONLY inputs. This pipeline reports; it does not fix.",
        "tex_structure": {
            "appendix_starts_line": app_idx + 1,
            "end_document_line": end_idx + 1,
            "dead_lines_after_end_document": len(lines) - (end_idx + 1),
            "tex_files_read": len([f for f in files_read if f["role"].startswith("tex")]),
        },
        "counts": {
            "cited_unique": len(cited),
            "cite_occurrences": len(all_live),
            "bib_unique_keys": len(bib),
            "bib_uncited": len(bib) - len(cited),
            "cited_in_body": len(set(body_keys)),
            "cited_in_appendix": len(set(appx_keys)),
            "appendix_only": len(set(appx_keys) - set(body_keys)),
        },
        "hygiene": {
            "duplicate_keys": {k: c for k, c in sorted(dup_counts.items()) if c > 1},
            "keys_only_after_end_document": dead_only,
            "uncited_bib_keys": sorted(set(bib) - set(cited)),
            "cite_commands_used": dict(cite_commands.most_common()),
            "unrecognised_cite_commands": unknown_cmds,
        },
        "references": records,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    c = payload["counts"]
    print(f"{tex_path}: \\appendix line {app_idx+1}, \\end{{document}} line {end_idx+1}")
    print(f"  dead lines after \\end{{document}} : "
          f"{payload['tex_structure']['dead_lines_after_end_document']} (excluded)")

    # THE FILE LIST IS NOT DECORATION. It is the only defence against the quietest failure in this
    # pipeline. A user who knows their paper is split across ten files, and sees one file listed
    # here, can catch a silent under-count in a second. If the extractor says nothing, nobody can.
    tex_files = [f for f in files_read if f["role"].startswith("tex")]
    print(f"\n.tex files read ({len(tex_files)}):")
    for f in tex_files:
        kind = "main" if f["role"] == "tex_main" else "child"
        print(f"    {f['citations']:>4} citations  [{kind:>5}]  {f['path']}")
    print(f".bib files read ({len(bib_paths)}):")
    for b in bib_paths:
        print(f"                        {b}")
    print()
    if nocite_all:
        print("  \\nocite{*} PRESENT: every .bib entry prints. Scope is the whole file.")
    # Rule 10. Show which citation commands the paper uses. If the user's paper is full of
    # \textcite and this line does not say so, the extractor is lying to them.
    print("Citation commands used : "
          + ", ".join(f"\\{k} ({v})" for k, v in cite_commands.most_common()))
    if unknown_cmds:
        print("\n  ** UNRECOGNISED CITATION COMMANDS **")
        for k, v in sorted(unknown_cmds.items()):
            print(f"     \\{k}  ({v} occurrences)")
        print("     Their keys HAVE been collected, so nothing is missing. But confirm these are")
        print("     citation commands, and add them to KNOWN_CITE_COMMANDS. If one of them is not")
        print("     a citation command, its argument is now in the reference list wrongly.\n")

    print(f"Cited unique keys      : {c['cited_unique']}  ({c['cite_occurrences']} occurrences)")
    print(f"  body / appendix      : {c['cited_in_body']} / {c['cited_in_appendix']}"
          f"  (appendix-only: {c['appendix_only']})")
    print(f".bib entries never cited: {c['bib_uncited']} of {c['bib_unique_keys']} "
          f"(they do not print and are NOT verified)")
    print(f"Cited but missing .bib : {len(missing_from_bib)}")
    print(f"Keys only in dead zone : {len(dead_only)}")
    print(f"Duplicate .bib keys    : {len(payload['hygiene']['duplicate_keys'])}")
    flagged = Counter(f for r in records for f in r["entry_flags"])
    print(f"Entry flags            : {dict(flagged)}")
    print(f"\nWrote {out_path}  ({len(records)} references)")

    # THE REPORT-FORMAT PREFLIGHT. Run it HERE, before a single reference is fetched.
    #
    # If the report is going to fall back to a generic citation format, the user must be told NOW,
    # not discover it in the finished report an hour later. By then their only choices are to
    # accept it or redo the run, and a fallback nobody offered them a chance to prevent is a
    # fallback they will rightly resent. Finding out costs one `which bibtex`. There is no excuse
    # for learning it late.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bst_render
        info = bst_render.preflight(bib_style, [str(main_dir), "."], engine)
        bst_render.report_preflight(info)
        if not info["can_render"]:
            print("  STOP HERE and put this to the user before running the tiers.\n")
    except Exception as exc:
        print(f"\n  (could not check report formatting: {exc.__class__.__name__})")


if __name__ == "__main__":
    main()
