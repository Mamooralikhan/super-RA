#!/usr/bin/env python3
"""
RENDER REFERENCES IN THE PAPER'S OWN BIBLIOGRAPHY STYLE.

Imported by 06_render.py. Not a pipeline step; it runs no tier and fetches nothing.

WHY THIS EXISTS
---------------
The report used to render citations in a house format we invented: every author inverted, the
year in parentheses. No journal on earth prints that. An author reading the report had to
mentally translate it back into their own bibliography before they could act on it, and a
"corrected" line they could not recognise is a line they will not trust.

The obvious fix is to reimplement the AER style, then the APSR style, then Chicago, and so on.
That is a bad idea and it gets worse with every style added: a hand-rolled formatter that is
subtly wrong makes a CORRECT entry look WRONG, which is the precise disease this pipeline exists
to cure.

So we do not reimplement anything. WE RUN THE AUTHOR'S OWN .bst FILE.

BibTeX needs no LaTeX compile and no document. It needs one .aux naming the style, the data, and
the keys. We hand it exactly that, it hands us back a .bbl formatted by the real style file, and
the result is not an approximation of AER: it IS AER, because aer.bst produced it.

    \\bibliographystyle{aer}  ->  aer.bst  ->  "Brule, Rachel and Nikhar Gaikwad, ``Culture,
                                               capital...,'' Journal of Politics, 2020."

The same mechanism gives apsr, chicago, econometrica, plainnat and anything else for free. We
support every style the user has installed, because we support none of them ourselves.

THE FALLBACK IS NOT OPTIONAL
----------------------------
ref-check promises it needs no LaTeX install. That promise stands. If BibTeX is not on the
machine, or the .bst cannot be found, this module returns None and 06_render falls back to the
generic format, SAYING SO PLAINLY in the report. A report that silently switches format is worse
than one that never had the feature.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# LaTeX accent and symbol commands that appear in .bbl output, mapped to the character.
ACCENTS = {
    ("'", "e"): "é", ("'", "a"): "á", ("'", "o"): "ó", ("'", "i"): "í",
    ("'", "u"): "ú", ("'", "c"): "ć", ("'", "n"): "ń", ("'", "s"): "ś",
    ("`", "e"): "è", ("`", "a"): "à", ("`", "o"): "ò", ("`", "i"): "ì",
    ("`", "u"): "ù",
    ('"', "o"): "ö", ('"', "a"): "ä", ('"', "u"): "ü", ('"', "e"): "ë",
    ('"', "i"): "ï",
    ("^", "o"): "ô", ("^", "a"): "â", ("^", "e"): "ê", ("^", "i"): "î",
    ("^", "u"): "û",
    ("~", "n"): "ñ", ("~", "a"): "ã", ("~", "o"): "õ",
    ("c", "c"): "ç", ("c", "s"): "ş",
    ("v", "s"): "š", ("v", "c"): "č", ("v", "z"): "ž",
}


def have_bibtex():
    return shutil.which("bibtex") is not None


def find_bst(style, search_dirs):
    """Locate <style>.bst: next to the paper first, then wherever the TeX installation keeps it."""
    if not style:
        return None
    for d in search_dirs:
        p = Path(d) / f"{style}.bst"
        if p.is_file():
            return str(p.resolve())
    if shutil.which("kpsewhich"):
        try:
            out = subprocess.run(["kpsewhich", f"{style}.bst"],
                                 capture_output=True, text=True, timeout=20)
            hit = out.stdout.strip().splitlines()
            if hit and Path(hit[0]).is_file():
                return hit[0]
        except Exception:
            pass
    return None


def _latex_to_html(s):
    """Turn one .bbl entry's LaTeX into HTML. Conservative: unknown macros are dropped, not guessed."""
    s = s.strip()
    s = re.sub(r"\\newblock\s*", " ", s)
    s = re.sub(r"\\harvardand\s*", "and", s)
    s = re.sub(r"\\bysame\s*", "", s)

    # Accents: {\'e}, \'{e}, \'e  -> the accented character.
    def acc(m):
        cmd, ch = m.group(1), m.group(2)
        return ACCENTS.get((cmd, ch), ch)
    s = re.sub(r"\{\\([\"'`^~vc])\{?(\w)\}?\}", acc, s)
    s = re.sub(r"\\([\"'`^~vc])\{(\w)\}", acc, s)
    s = re.sub(r"\\([\"'`^~])(\w)", acc, s)

    # Emphasis. Handle the {\bf ...} / {\it ...} group form and the \textbf{...} form.
    for tex, tag in (("bf", "b"), ("it", "i"), ("em", "i"), ("sc", "span")):
        s = re.sub(r"\{\\%s\s+([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}" % tex,
                   lambda m, t=tag: f"<{t}>{m.group(1)}</{t}>", s)
    s = re.sub(r"\\textbf\{([^{}]*)\}", r"<b>\1</b>", s)
    s = re.sub(r"\\textit\{([^{}]*)\}|\\emph\{([^{}]*)\}",
               lambda m: f"<i>{m.group(1) or m.group(2)}</i>", s)
    s = re.sub(r"\\urlprefix|\\url\{([^{}]*)\}", lambda m: m.group(1) or "", s)

    # Quotes and dashes. NOTE: `` '' are LaTeX quotes, not code. Use HTML entities, which are
    # ASCII and therefore pass the repository's no-em-dash gate.
    s = s.replace("``", "&ldquo;").replace("''", "&rdquo;")
    s = s.replace("---", "&mdash;").replace("--", "&ndash;")
    s = s.replace("~", " ").replace("\\&", "&amp;").replace("\\_", "_").replace("\\%", "%")
    s = re.sub(r"\\[ ,;!]", " ", s)                # \  \, \; \! are spacing macros, not text.
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)          # any macro we do not know: drop it
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    return s


def _parse_bbl(bbl):
    """Pull {key: formatted_html} out of a .bbl.

    Two entry macros in the wild: \\bibitem[..]{key} (natbib and friends) and \\harvarditem
    [..]{..}{year}{key} (the harvard family, which aer.bst uses). Match either.
    """
    body = bbl
    m = re.search(r"\\begin\{thebibliography\}(?:\{[^}]*\})?", body)
    if m:
        body = body[m.end():]
    body = body.split("\\end{thebibliography}")[0]

    # THE BRACE GROUP MUST BE NESTING-AWARE. `[^{}]*` looks right and is not: \harvarditem's
    # label group routinely contains an accent, as in {Brul{\'e} and Gaikwad}, and a flat
    # character class cannot cross that inner brace. The consequence was not an error. It was
    # the accented entry SILENTLY VANISHING from the rendered report while every unaccented
    # entry rendered fine. Same disease as every other guard in this pipeline: a parser that
    # drops data quietly and lets the run look clean.
    GROUP = r"\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}"

    marker = re.compile(
        r"\\(?:bibitem|harvarditem)\s*(?:\[[^\]]*\])?\s*"      # \bibitem[...]  or \harvarditem[...]
        r"(?:" + GROUP + r"\s*" + GROUP + r"\s*)?"             # harvarditem's two extra groups
        r"\{([^{}]+)\}"                                        # the KEY
    )
    hits = list(marker.finditer(body))
    out = {}
    for i, h in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(body)
        out[h.group(1).strip()] = _latex_to_html(body[h.end():end])
    return out


def render(entries, style, search_dirs, timeout=90):
    """Render {key: bibtex_source} through the paper's real .bst.

    Returns (rendered, note):
      rendered -- {key: html}, or None if we could not do it
      note     -- one plain sentence for the report, saying exactly what happened

    NEVER PUT THE ORIGINAL AND THE CORRECTED VERSION OF THE SAME REFERENCE IN ONE CALL.
    Call this once for the originals and once for the correcteds. See render_pair() below, and
    use that instead of calling this directly.

    A bibliography style is not a per-entry formatter. It sees the whole list, and it deliberately
    formats entries in the light of their NEIGHBOURS. Put a reference and its corrected twin in
    one run and they sort adjacently, at which point:

      * \\bysame fires. The style suppresses the repeated author name, because that is what a
        bibliography does when consecutive entries share an author. The corrected line rendered
        as ",, and ," with the names simply gone.
      * The year gains a disambiguating suffix: 2016 becomes "2016a" and "2016b", because the
        style sees two entries by the same authors in the same year.

    Both artifacts are the style file behaving CORRECTLY, and both are poison in a report: they
    make a correct corrected entry look mangled, and they invent a year suffix the paper does not
    print. Keep the two lists apart and neither can happen.

    Never raises. A failure here must degrade the report's formatting, never break the run: the
    findings are the deliverable, and they do not depend on how prettily they are printed.
    """
    if not entries:
        return None, "No entries to render."
    if not have_bibtex():
        return None, ("BibTeX is not installed on this machine, so references below are shown in a "
                      "generic format rather than in the paper's own bibliography style.")
    bst = find_bst(style, search_dirs)
    if not bst:
        return None, (f"The paper declares \\bibliographystyle{{{style}}}, but {style}.bst could not "
                      "be found, so references below are shown in a generic format rather than in "
                      "the paper's own style.")

    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            shutil.copy(bst, td / Path(bst).name)
            (td / "refs.bib").write_text("\n\n".join(entries.values()), encoding="utf-8")
            aux = ["\\relax"] + [f"\\citation{{{k}}}" for k in entries]
            aux += [f"\\bibstyle{{{Path(bst).stem}}}", "\\bibdata{refs}"]
            (td / "job.aux").write_text("\n".join(aux) + "\n", encoding="utf-8")

            subprocess.run(["bibtex", "job"], cwd=td, capture_output=True,
                           text=True, timeout=timeout)
            bbl = td / "job.bbl"
            if not bbl.is_file():
                return None, ("BibTeX produced no output, so references below are shown in a "
                              "generic format rather than in the paper's own style.")
            rendered = _parse_bbl(bbl.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return None, (f"The paper's bibliography style could not be applied ({exc.__class__.__name__}), "
                      "so references below are shown in a generic format.")

    if not rendered:
        return None, ("BibTeX returned nothing usable, so references below are shown in a generic "
                      "format rather than in the paper's own style.")

    return rendered, (f"References below are rendered by the paper's own <code>{style}.bst</code>, "
                      "so they read exactly as they print in the paper. Both the original and the "
                      "corrected line go through the same style file.")


def render_each(entries, style, search_dirs, timeout=60):
    """Render each entry in ITS OWN BibTeX run, so no entry has a neighbour.

    ONE RUN PER REFERENCE. THIS IS NOT PARANOIA, AND TWO RUNS WERE NOT ENOUGH.

    A bibliography style formats entries in the light of the ones next to them, which is right
    for a bibliography and poison for a report. Two failures were observed, both of them the
    style file behaving CORRECTLY:

      1. \bysame. When consecutive entries share a leading author the style suppresses the
         repeated name (the "----" convention). Splitting originals from correcteds did not fix
         it, because two DIFFERENT references can share a first author: jayachandran2015genderroots
         sorts right before jayachandranvoena2026, so the latter rendered as
         "and Alessandra Voena", with "Jayachandran, Seema" simply gone.
      2. Year disambiguation. Two entries by the same authors in the same year become "2016a" and
         "2016b", inventing a suffix the paper does not print.

    In a bibliography, a row is read in the context of its neighbours. IN A REPORT, EVERY ROW IS
    READ ALONE. So every row must be FORMATTED alone. One entry, one run, no neighbours, nothing
    to suppress and nothing to disambiguate against.

    The cost is one BibTeX process per reference, which is milliseconds, and it buys a guarantee
    rather than a hope.
    """
    if not entries:
        return {}, "No entries to render."
    if not have_bibtex():
        return None, ("BibTeX is not installed on this machine, so references below are shown in a "
                      "generic format rather than in the paper's own bibliography style.")
    bst = find_bst(style, search_dirs)
    if not bst:
        return None, (f"The paper declares \\bibliographystyle{{{style}}}, but {style}.bst could not "
                      "be found, so references below are shown in a generic format rather than in "
                      "the paper's own style.")

    out = {}
    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            shutil.copy(bst, td / Path(bst).name)
            stem = Path(bst).stem
            for key, src in entries.items():
                (td / "refs.bib").write_text(src, encoding="utf-8")
                (td / "job.aux").write_text(
                    f"\\relax\n\\citation{{{key}}}\n\\bibstyle{{{stem}}}\n\\bibdata{{refs}}\n",
                    encoding="utf-8")
                for stale in ("job.bbl", "job.blg"):
                    (td / stale).unlink(missing_ok=True)
                subprocess.run(["bibtex", "job"], cwd=td, capture_output=True,
                               text=True, timeout=timeout)
                bbl = td / "job.bbl"
                if bbl.is_file():
                    got = _parse_bbl(bbl.read_text(encoding="utf-8", errors="replace"))
                    if key in got:
                        out[key] = got[key]
    except Exception as exc:
        return None, (f"The paper's bibliography style could not be applied "
                      f"({exc.__class__.__name__}), so references below are shown in a generic format.")

    if not out:
        return None, ("BibTeX returned nothing usable, so references below are shown in a generic "
                      "format rather than in the paper's own style.")

    return out, (f"References below are rendered by the paper's own <code>{style}.bst</code>, so they "
                 "read exactly as they print in the paper. Each reference is formatted on its own, "
                 "so no entry borrows or suppresses anything from its neighbours.")


def render_pair(originals, correcteds, style, search_dirs):
    """THE ENTRY POINT. Render both columns, every reference formatted in isolation.

    Both columns go through the SAME .bst. They must: if they were formatted by different styles,
    a difference in FORMATTING would read to the author as a difference in the DATA, and the
    report would accuse them of an error that exists only in our renderer.
    """
    ro, note = render_each(originals, style, search_dirs)
    if ro is None:
        return None, note
    rc, _ = render_each(correcteds, style, search_dirs) if correcteds else ({}, note)
    rc = rc or {}

    out = {}
    for key in set(originals) | set(correcteds or {}):
        out[key] = {"original": ro.get(key), "corrected": rc.get(key)}
    return out, note


def preflight(style, search_dirs, engine=None):
    """CAN WE PRINT THE REPORT IN THE PAPER'S OWN STYLE? Answer this BEFORE the run, not after.

    Returns a dict:
        can_render : bool
        style      : the style the paper declares, or None
        reason     : why not, in one plain sentence (empty when can_render)
        remedies   : list of things the USER can actually do about it

    THE POINT IS THE TIMING. If the report is going to fall back to a generic format, the user
    must be told BEFORE the tiers run, not discover it in the finished report an hour later. By
    then the choice is take-it-or-redo-it, and a fallback the user was never offered a chance to
    prevent is a fallback they will reasonably resent.

    It is also cheap. Finding out costs one `which bibtex` and one `kpsewhich`. There is no excuse
    for learning it late.
    """
    info = {"can_render": False, "style": style, "engine": engine, "reason": "", "remedies": []}

    if engine == "biblatex":
        info["reason"] = ("The paper uses biblatex, which has no \\bibliographystyle line and is "
                          "driven by biber rather than BibTeX. References will be shown in a "
                          "generic format, not in the paper's own style.")
        info["remedies"] = [
            "Tell me the traditional BibTeX style closest to your biblatex style (for example "
            "'aer', 'apsr', 'chicago', 'plainnat') and I will render the report through that .bst.",
            "Or accept the generic format: it changes nothing about the FINDINGS, only how the "
            "citations are typeset in the report.",
        ]
        return info

    if not style:
        info["reason"] = ("The paper declares no \\bibliographystyle, so I do not know how its "
                          "references are meant to print. They will be shown in a generic format.")
        info["remedies"] = [
            "Tell me the style your journal wants (for example 'aer', 'apsr', 'chicago') and I "
            "will render the report through that .bst.",
        ]
        return info

    if not have_bibtex():
        info["reason"] = (f"The paper uses \\bibliographystyle{{{style}}}, but BibTeX is not "
                          "installed on this machine, so I cannot render through it. References "
                          "will be shown in a generic format.")
        info["remedies"] = [
            "Install a TeX distribution and re-run step 06 only. On macOS: "
            "`brew install --cask basictex`. On Debian or Ubuntu: `apt install texlive-bibtex-extra`. "
            "Nothing else in the pipeline needs it, and no reference has to be re-fetched.",
            "Or accept the generic format. It changes nothing about the FINDINGS.",
        ]
        return info

    bst = find_bst(style, search_dirs)
    if not bst:
        info["reason"] = (f"The paper asks for {style}.bst, and BibTeX is installed, but that style "
                          "file is not on this machine. References will be shown in a generic format.")
        info["remedies"] = [
            f"Copy {style}.bst into the folder next to the paper, and re-run step 06 only. No "
            "reference has to be re-fetched.",
            f"Or install the package that ships it, then re-run step 06. `tlmgr install {style}` "
            "often does it.",
            "Or name a style you DO have, and I will use that instead.",
        ]
        return info

    info["can_render"] = True
    info["bst"] = bst
    return info


def report_preflight(info):
    """Print the preflight so a human reads it. Called by step 01, before any tier runs."""
    print("\nREPORT FORMATTING")
    if info["can_render"]:
        print(f"  The report will print your references in your paper's own style "
              f"(\\bibliographystyle{{{info['style']}}}).")
        print(f"  Using: {info['bst']}")
        return
    print("  *** THE REPORT WILL FALL BACK TO A GENERIC CITATION FORMAT. ***\n")
    print(f"  {info['reason']}\n")
    print("  This does NOT affect a single finding. Every error found is still found, and every")
    print("  link is still checked. It affects only how the citations are TYPESET in the report.\n")
    print("  What you can do about it:")
    for r in info["remedies"]:
        print(f"    - {r}")
    print()
