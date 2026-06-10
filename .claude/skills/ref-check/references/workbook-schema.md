# Workbook Schema

Use this schema when building or upgrading the review workbook.

The workbook is a review artifact. It should preserve the paper's current citation text while making it easy for the user to compare that text with the source page and inspect unresolved problems.

## Base Columns

- `Original paper reference`
- `Reference from DOI/Link`
- `Incorrect DOI or Link`

## Hidden Helper Columns

- citation key
- section
- DOI or URL used

## Review Columns

- `Review status`
- `Source status`
- `Author seq`
- `Year`
- `Title / venue`
- `Vol / issue`
- `Pages / article no.`
- `DOI`
- `WP / report status`
- `Update needed`
- `Automated notes`

## Status Conventions

### Review Status

- `OK`
- `No source link`
- `Needs source check`
- `Needs metadata review`
- `Incorrect link`
- `hallucinated`

### Update Needed

- `No`
- `Yes`
- `Search source`
- `Fill source ref`
- `Check publication`

## User Review Focus

Use the workbook to help the user verify:

- incorrect links
- possible hallucinated references
- missing or incorrect year, DOI, volume, issue, pages, or venue metadata
- whether a working paper appears to have a later journal version

## Color Conventions

- Green: source aligned or no action needed
- Yellow: review needed or search needed
- Red: incorrect link or substantive mismatch
- Gray: not present or unfilled

## Notes Discipline

Keep notes short. Prefer:

- `No DOI/URL in this row.`
- `Link exists, Column B blank.`
- `User confirmed incorrect link.`
- `Check: Year, DOI.`
- `WP/report label may need updating.`
