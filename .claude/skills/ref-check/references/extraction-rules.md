# Extraction Rules

Read this before writing or adapting the extractor.

Extraction looks like the boring part of this pipeline. It is not. It is where the pipeline is most likely to do real harm, because **a bad extractor does not fail loudly. It invents a defect in a bibliography that is actually correct**, and then three tiers of careful verification faithfully investigate a problem that never existed.

Every rule below was learned from a bug that did exactly that on the real run.

## Rule 1: Only cited keys print

Absent `\nocite{*}`, a `.bib` entry that no `\cite` command reaches is never typeset. It does not appear in the bibliography, and it cannot be wrong in the paper because it is not in the paper.

On the reference paper, `all_references.bib` held **175 unique entries and the paper cited 66**. Verifying all 175 would have been more than 2.5 times the work, for zero effect on the submitted document.

Establish this count first and tell the user, before committing them to a long run.

Check for `\nocite{*}` explicitly. If it is present, every entry prints and the scope is the whole file.

## Rule 2: Truncate at `\end{document}`

Anything after `\end{document}` is dead. It does not compile and it does not print. Authors routinely park old sections, abandoned tables, and draft paragraphs down there.

The reference paper had **865 lines of dead content** after `\end{document}`, containing citations. Extracting them would have added references to the report that do not exist in the paper.

## Rule 3: Strip unescaped `%` comments

A commented-out `\citep{foo}` does not print. Strip from the first unescaped `%` to end of line, on every line.

`\%` is a literal percent sign, not a comment. Do not strip on it.

## Rule 4: Duplicate `.bib` keys are first-wins

BibTeX keeps the **first** definition of a repeated key and silently discards the rest. Your parser must do the same, or your report describes an entry the reader never sees.

This matters more than it sounds. On the reference paper, ten keys were duplicated. For one of them, the **first copy was missing its `journal` field while the later copies had it**, so the bibliography was rendering that entry without a journal name. A last-wins or merge-everything parser would have shown a complete entry and reported no problem.

Report duplicates in the hygiene panel. Say which of them actually print. Never merge them silently.

## Rule 5: Use a brace-aware field parser, not a line-anchored regex

BibTeX does not care about newlines. An entry can be written entirely on one line:

```bibtex
@inbook{Fearon_1999, place={Cambridge}, title={Electoral Accountability...}, booktitle={Democracy, Accountability, and Representation}, publisher={Cambridge University Press}, author={Fearon, James D.}, year={1999}, pages={55--97}}
```

A regex anchored to line-start, such as `(?m)^\s*(\w+)\s*=`, extracts **zero fields** from that entry. The record then looks like an empty stub.

This is exactly what happened. The entry was flagged a stub, the Assistant was handed a record with no title and no author, it correctly reported that it could not identify a work from a surname and a year, and the report said "not found" about a perfectly good citation to a well-known Cambridge University Press chapter. **The pipeline behaved correctly on corrupt input. The corruption was ours.**

Walk the entry body instead, tracking brace depth and quote state, and split on commas at depth zero. That is what BibTeX itself does. See `parse_fields()` in `pipeline/01_extract_citations.py`.

## Rule 6: Split entries on a leading-whitespace `@`

Splitting on `\n@` misses an entry that is indented:

```bibtex
}

 @article{Sharma_2022,
   title={...},
```

BibTeX accepts the leading space. A `\n(?=@)` split does not, so that entry is never recognised as its own entry. Worse, **it gets swallowed into the preceding entry, and its fields are merged into that entry's field set**, corrupting a neighbour that was perfectly fine.

Split on `\n(?=[ \t]*@)`.

## Rule 7: Assert, then halt

Before any web work begins, the extractor must assert:

- the cited key count matches what was reported to the user
- **zero** cited keys are missing from the `.bib`
- **zero** keys were drawn from after `\end{document}`
- **zero** `\input`/`\include` targets failed to resolve on disk (Rule 8)

If an assertion fails, halt. Do not proceed with a partial or suspect reference list. A wrong list produces a confidently wrong report, which is worse than no report.

## Rule 8: Follow `\input` and `\include`, and follow them last

A paper split across `sections/*.tex` keeps its citations **in the children**. An extractor that reads only the main file cannot see them.

This is the quietest failure in the whole pipeline, and the quietness is the danger. It does not raise an error. It does not warn. It simply reports fewer references, and **every assertion in Rule 7 still passes**, because a citation the parser never saw cannot be reported as missing from the `.bib`. The run looks clean. The report looks confident. Half the paper was never checked.

On the fixture built to test this rule, a main file plus three children cites four distinct works. An extractor that reads only the main file reports **one**, and reports it cheerfully.

Resolve `\input{...}`, `\include{...}` and `\subfile{...}` recursively, relative to the **main document's** directory (that is TeX's own rule: a grandchild resolves against the main directory, not against its parent's). The `.tex` extension is optional and usually omitted. A `\subfile` child is a compilable document in its own right, so splice in only what sits between its `\begin{document}` and `\end{document}`.

### The order is load-bearing, and it is not the obvious one

**Rule 2 and Rule 3 both run before this rule. Both must.** The reference paper proves each case, and getting either backwards produces a false result of a different kind:

- It `\input`s about **fifteen table files after `\end{document}`**. Expanding before truncating drags the entire dead zone back in through the side door, defeating Rule 2 completely.
- It contains **three commented-out `\input` lines whose targets do not exist on disk** (`main.tex` lines 149, 980, 1041). Resolving children before stripping comments halts the pipeline on three files that TeX itself never reads. That is a false failure, and a false failure is the same disease as a false accusation.

The correct sequence is therefore: **truncate at `\end{document}`, then strip comments, then resolve children.** It was verified both ways round on the reference paper: the identical `\input` line is harmless when commented and a hard halt when live.

### Never guess at a missing child

If a live `\input` target cannot be found on disk, **halt**. An unresolved child is an unknown number of unchecked citations, and proceeding on an unknown is the one thing this pipeline exists never to do.

### Print the file list

Print every file read and the citation count each contributed. This is the only defence a user has against the silent under-count. Someone who knows their paper is split across ten files, and sees one file listed, catches the fault in a second. If the extractor says nothing, nobody can catch it, and the report will be wrong in a way that looks exactly like being right.

## Rule 9: Find `\begin{document}` before you look for `\appendix`

The body and the appendix are split at `\appendix`. The obvious way to find it, "the first line that starts with `\appendix`", is wrong, and like every other rule here it is wrong **silently**.

Papers define appendix macros in the preamble:

```latex
\newcommand*\appendixwithtoc{%
  \appendix                      <- the naive scan stops HERE, in the preamble
  \addcontentsline{toc}{section}{Appendix}}
\renewcommand\appendixname{Online Appendix}
\begin{document}
...
\appendix                        <- the real one, 590 lines later
```

A scan that takes the first hit lands inside the macro body. It then treats the **preamble** as the body of the paper, which cites nothing, and the **entire document** as the appendix.

This was found on a real paper during the pilot. The extractor reported **all 35 references as appendix-only and zero in the body**, in a clean table, with no error and no warning. The cited set was still correct, because body plus appendix covers the same lines either way, so nothing downstream complained. Only the classification that goes into the report was garbage, and a reader who noticed would stop trusting the rest of the page.

Two conditions, and you need both:

1. **Look for `\appendix` only after `\begin{document}`.** This is what excludes preamble macro definitions. It is also simply correct: nothing in the preamble is typeset.
2. **Use a word boundary.** `\appendixwithtoc` and `\appendixname` both begin with the characters `\appendix`. Match `\\appendix(?![A-Za-z@])`, not a bare prefix.

The body therefore runs from `\begin{document}` to `\appendix`, and the appendix from `\appendix` to `\end{document}`. If there is no `\begin{document}` at all, halt: the user has handed you a child file, not the main paper.

## Rule 10: Catch every citation command, including the ones you have never heard of

A citation command the extractor does not know about contributes **nothing**, and says nothing about it. The paper prints the reference; the report never mentions it. This is the same silent under-count as Rule 8, arriving through a different door, and Rule 7's assertions cannot catch it either: a citation the parser never saw cannot be reported as missing from the `.bib`.

The old regex named eight natbib commands. **Fourteen of twenty-four real citation commands were invisible to it**, including:

| Family | Invisible commands |
|---|---|
| natbib, capitalised | `\Citep`, `\Citet`, `\Citeauthor`. These are the **sentence-start** forms, so they are common. |
| biblatex, all of it | `\parencite`, `\textcite`, `\autocite`, `\footcite`, `\supercite`, `\fullcite`, `\smartcite` |
| apacite | `\citeA`, `\shortcite`, `\citeN` |
| natbib | `\nocite{key}`, which **does** print that entry |

A paper that mixes `\citep` with `\textcite` loses every `\textcite`, silently, and the run still looks clean.

### The fix is not a longer list

Enumerating every command that every citation package will ever ship is a game you lose on the next release. So do not try.

**Match any macro whose name contains "cite", take its keys, and name the ones you do not recognise.** Missing a citation command then becomes structurally impossible. The worst case is that you *over*-collect: some unrelated macro's argument enters the key list, and Rule 7 catches it immediately and loudly by finding a "key" that is not in the `.bib`.

That asymmetry is the whole argument. **Over-collecting fails noisily. Under-collecting fails silently.** When you must guess, always guess toward the noisy failure.

An unrecognised command is therefore **reported, not dropped**. Its keys are already in the reference list. The report exists so a human can confirm it really is a citation command, and add it to the known list.

### Details that bite

- **Brace-aware, not regex-aware.** A key list is a brace group.
- **`\nocite{*}` contributes no key.** It is a change of scope (Rule 1), not a citation of a work called `*`.
- **Only the plural forms take a run of brace groups.** `\cites{a}{b}{c}` is real biblatex. But if you allow a run for every command, then `\citet{smith} {and others}` swallows the following brace group and invents a key called "and others".
- **Print the census.** Show which citation commands the paper actually uses, and how often. If a user's paper is full of `\textcite` and the extractor does not say so, it is lying to them.

## Entry flags: the pipeline's own work items

A `.bib` file has no editorial comments, so the extractor computes its own "this one is already known to be shaky" signals and passes them to the Assistant as **context for where to search hardest**:

- `duplicate_key`
- `missing_required_fields`
- `no_doi`
- `forward_dated` (dated in the current year or later, so probably a working paper)
- `institutional_author` (the author string names an organisation)
- `stub_entry` (too empty to check against anything)

**These are context, not instructions.** They tell a tier where to look. They never license it to overwrite the author's choices. An `institutional_author` flag in particular means the institution **is** the author and must not be replaced by a staff member's name found in a catalogue.

## A closing warning

Most of the eight rules above were discovered **after** the pipeline had already produced a confident, well-formatted, entirely wrong finding about a specific reference, or would have done. Every time, the finding looked completely plausible.

Do not trust an extractor because its output looks reasonable. Trust it because its assertions pass and because you read the first batch by hand.
