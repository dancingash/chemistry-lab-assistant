# Formulations and experiment batches

Use this module when the user describes ingredient ratios/amounts and asks for formulation
calculation, gradients, repeats, a batch recipe Excel, or completion of a previously designed batch.
Read `{program}/scripts/lab_formulations_contract.md` before preparing tool inputs.
Use installed Python and the usual resolved private data root; never store real data in the package.

## Design and calculate

1. Read only the relevant project/stage, route and explicitly selected baseline. Resolve an existing
   stage's designated best numerically when no baseline is named; if absent, ask for the baseline.
   A new process can start from the user's supplied recipe. Preserve unmodified conditions.
2. Translate natural-language inputs into the structured recipe; do not ask the user to fill JSON.
   The user chooses materials and conditions. Support specified gradients and independent repeats.
   Clarify wet/dry/effective-component basis, ambiguous units and zip versus full combinations only
   when they change the meaning. Keep missing properties pending while calculating clear quantities.
3. Use `preview` for deterministic Decimal arithmetic. Show a compact per-group table with units,
   bases, parameter sources and unresolved inputs. Verify required chemical constants against supplied
   or authoritative sources; never invent density, purity, solids or functionality. Pending results
   must not appear as zero. A zero-addition control is a real zero.
4. `save` the batch and pinned planned versions. This creates no experimental facts, sample numbers,
   best designation or daily observations. Revisions preserve old inputs and references.
   Allocate a new batch ID with an ASCII prefix plus UUID for a genuinely new batch; reuse its
   exact batch ID only for requested revisions. Allocate operation IDs once and preserve them on retry.
5. Use Spreadsheets for the Excel deliverable. Call `load_workspace_dependencies`, then `export`
   with its actual Node and package paths. Render and inspect every generated worksheet page listed
   in `.qa.json`; confirm arithmetic comparisons and input-change verification. Keep the saved batch
   if the engine is unavailable, and accurately report the missing export/QA. Render changed plan
   Word exports using Documents and the existing supported fallback when needed.

## User confirms work is complete

- Resolve the batch AND revision from context or `list`/`show`. Only confirmed groups enter the daily;
  other groups remain planned. If several batches could be “this batch”, ask which one.
- The user's “completed” is sufficient authorization for daily entry. Save that fact directly.
  Preserve recipe amounts as planned; unreported actual weighings, deviations and results stay 待补.
  An explicit “as planned” substantiates reported conditions, never measured precision or yield.
- Use reported dates and source sample IDs. Pass the conversation's numeric UTC offset when defaulting
  dates. For new synthesis, use its actual start date for sample creation when supplied. If the user
  only confirms completion today, the tool discloses any provisional creation date assumption.
- Set the state to the reported progress: pending post-treatment/testing when applicable. Do not
  interpret completion of one operation as confirmation of unreported test results.
- Use `complete` with a stable operation ID and the user's completion words. Reported deviations
  use `observed_patch` or actual material rows. Reuse EXACT input on interrupted writes. Never
  allocate another sample or operation to bypass a failure. Changed facts use the daily correction
  workflow and the original record ID.
- Apply the daily module's Word/tracker render checks. Return recorded group/sample IDs, dates,
  states and pending data. Daily refresh can recover batch metadata and reverse plan links from Word.

Excel is an export of the selected recipe revision. Editing cells does not update authoritative
batch data or establish execution. Apply changes through an explicit recalculation/save request;
do not overwrite a hand-edited export. All examples in the contract are synthetic software data.
