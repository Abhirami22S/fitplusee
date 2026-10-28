# Change log: supervised versions of the Word and PowerPoint deliverables

Written 27 Oct 2026. Every new file is a COPY saved next to its original; no original was opened for editing, and each original's SHA-256 was re-checked after the work (table 1). Nothing was deleted, nothing was committed, and `.gitignore`, the `exports/` CSVs and the cross-check script were not touched. Numbers are listed here, with their sources, and not in the document bodies, as requested. **Second pass, 27 Oct 2026** (after the review of the [CONFIRM] items): only the four `_supervised` copies were edited again (sections 3b, 4, 5b); the pre-edit copies are kept outside the project in the Claude scratch folder (`work/pre_confirm_backup/`). **Third pass, 27 Oct 2026:** the old Power BI screenshot was removed from deck slide 13 and replaced by a visible placeholder, and the stale draft PDF was renamed (sections 3c and 4); only the deck changed in this pass.

## 1. Files produced

| Document | New file (size, SHA-256) | Original (SHA-256 re-checked: unchanged) |
|---|---|---|
| Report v3 | `D:\bigdata\FitPulse_Report_Updated_v3_supervised.docx` (242,233 bytes, `B52BBD6075C4FCFABD88F20625DBD3BDE6A9E1FA94D05F553DF1D024B3C3A3CB`) | `D:\bigdata\FitPulse_Report_Updated_v3.docx` (`2E28E235BF1779A627DCA76A2E47C0A0205C950D2AA569744AB1A751711C7DBD`) |
| Deck v2 | `D:\bigdata\final_fitpulseppt_v2_supervised.pptx` (407,762 bytes, `E9816995DD1F5E9AE8444738CB802B83D4AA9CC7ADA7A3F6A0A25207446CBB48`) | `D:\bigdata\final_fitpulseppt_v2.pptx` (`5B66CB2A00C19ADDEE05AA5C1B3617FBBE238460C38A58CA5E088CA4A2D46BC7`) |
| ML-part guide | `D:\bigdata\fitpulsee\Abhirami_ML_Part_Implementation_and_Viva_supervised.docx` (49,324 bytes, `5B48257DD9115BBF40C534F6C539F4B6222FFCB7354E4F7A499957E146384D5F`) | `D:\bigdata\fitpulsee\Abhirami_ML_Part_Implementation_and_Viva.docx` (`B09C4E5E07F66CCCF48C4158ABE6B673D2E1F5066F2F29EBB22B9407C7F98029`) |
| Member-contributions review | `D:\bigdata\FitPulse_member_contributions_review_supervised.docx` (53,480 bytes, `DEB6349E86A675D7DAA175D98866CACCC5DD8CF5E15FC99069270AE6CC8E6F15`) | `D:\bigdata\FitPulse_member_contributions_review.docx` (`FA1D68CC772DBA0900F35CCAA0227923B8750EFB7198E447050EA5346110223B`) |

Not touched: `final_fitpulseppt_v2.pdf` (the PDF of the old deck, now out of date), `final_fitpulseppt_v2_review.docx` (the v2 change report with images of the old slides), the older drafts, and the three historical `.md` files.

Sizes and hashes in table 1 are those after the third pass (for the three Word files the same as after the second pass; the deck changed again, see 3c). After the second pass the deck was 561,866 bytes `B41C8330FE61D174...`. Before the second pass (first pass, same day) they were: Report v3 242,146 bytes `6F892DF11ADD1E77...`; Deck v2 561,893 bytes `BABA6A49089CF6D0...`; ML-part guide 49,367 bytes `B973F2FC88192394...`; Member-contributions review 53,520 bytes `98BCFD5631AE7C15...`. Page counts after the second pass: Report 22, deck 16, guide 25, member review 10 (unchanged). **The draft PDF exported before the second pass no longer matches the deck; it was renamed to `final_fitpulseppt_v2_supervised_STALE_do_not_use.pdf` in the third pass** (section 4, item 3); it was not deleted, not overwritten and its content is byte-identical, and no new PDF was exported, as instructed.

## 2. How the rules were applied

- **Allowed sources.** A number may come from `exports/E<n>_results.csv`, a CSV in `faculty_evidence/supervised/`, or `SUPERVISED_REPORT.md`. Section 5 gives the source of every number I wrote or changed. The column *also in SUPERVISED_REPORT.md* is a second check: it says whether the same figure string appears in that report (a `no` is usually a different rounding or a percentage, not a disagreement).
- **Not from a CSV.** File modification times, file listings, row counts of evidence files and the E1 script facts come from `SUPERVISED_REPORT.md` sections 5.1 and 5.3 (they are marked in the source column). The values quoted from `E2_nofuture_allusers_check.csv` and `sklearn_crosscheck*.csv` were computed from those files.
- **Unchanged sentences.** Numbers in sentences I did not rewrite (dataset facts, the HDFS and Power BI sections written by the other members, Appendix A of the guide, which the second pass re-checked, see 5b) were left as they were and were NOT re-sourced. They are listed in section 6.
- **`[CONFIRM]`.** A number I could not tie to an allowed source is either kept with a visible `[CONFIRM]` tag or removed; section 4 lists every tag.
- **No old-vs-new comparison.** The old Review 2 figures are not quoted or compared anywhere in the new files.
- **Two sentences you asked to be plain.** E2 is described as weak and E3 and E4 as showing no reliable skill in all four documents; E1's weight_kg caveat is stated as a limitation with no ablation and no number; the derived-data caveat (calories, distance, minutes, maximum heart rate, sleep quality) is kept.
- **Checks run on every file.** The skill validator for the format, a scan of the whole package for K-Means, silhouette, cluster, segment, unsupervised, PCA, elbow and the old numbers (34.44, 0.3528, 0.3413, 45,306/54,816, 228/209, 0.2018), and a visual check of every page or slide rendered by Microsoft Word or PowerPoint. For the Report, numbering of tables, figures and listings and every cross-reference were also checked by script.

## 3. Edits

### Report v3

- **Section 3 (3. CLUSTERING PROBLEM, 3.1-3.6):** Removed in full: Tables 13-18, Listings 5-9, Figures 3-5 (and their 3 embedded images); replaced by the supervised E3/E4 section below
- **1.1 Project Overview, para 2:** Rewritten for the five supervised experiments E1-E5; E5 numbers re-read from exports/E5_results.csv; states E2 weak and E3/E4 no reliable skill
- **1.3 System Architecture, para 1:** Removed 'clusters'; outputs described as predictions and evaluation results exported as CSV for Power BI
- **Table 2 (rows MLlib, Predictions / Clusters, Power BI Dashboard):** Removed K-Means and 'segments'; stage renamed 'Predictions'; Power BI row says built from CSV exports and carries a [CONFIRM]
- **1.4 Data Preprocessing, para + Table 3:** K-Means removed from the normalization/split wording; protocols of E1-E5 stated; Table 3 'Applies To' cells updated
- **1.5 Machine Learning Models, para + Table 4:** Table 4 rebuilt as the five supervised experiments (K-Means row removed); paragraph rewritten
- **Heading 2:** Renamed '2. CLASSIFICATION PROBLEM (E1, E2)'
- **2.1 Problem Statement, new paragraph after para 2:** Added the E2 definition (next-day goal, chronological split sizes and cut dates)
- **Table 5:** Row labels prefixed 'E1'; two rows added for E2 (target and the 20 input features, names from final_feature_set_E1_E5.csv); caption extended
- **2.2 Model Selection, hyperparameter paragraph:** Rewritten; the unconfirmed Random Forest grid is replaced by a [CONFIRM]; added a paragraph on the Logistic Regression and GBT comparison models and their E1 grids - **Second pass:** the [CONFIRM] was replaced by the search grid and its validation values (3b, 5b).
- **2.3 Implementation / Coding, intro:** Source of the E1/E2 numbers stated (supervised scripts); old sentence 'results were computed by running this code' replaced; reproduction difference read from E1_reproduction_check.csv
- **Table 8:** Rebuilt from exports/E1_results.csv: the weighted precision/recall rows (not in the results CSV) replaced by F1 macro and weighted; all values re-read
- **Tables 9 and 10:** Not changed: every value was verified against faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv and exports/E1_feature_importance.csv (exact match)
- **Captions and cross-references in 2.5/2.6:** Old Table 11 -> Table 12 and old Table 12 -> Table 13 (caption and the sentence 'Table 12 shows how predictions translate into personalized recommendations')
- **2.4 Results, new text + new Table 11 (before 2.5):** Added Table 11 (E1 random, E1 user-held-out, E2 chronological; three models and baselines) and a paragraph stating plainly that E2 is weak; all values from exports/E1_results.csv and E2_results.csv
- **2.5 Inference, result-specific paragraph:** Rewritten with values re-read from the CSVs; the two unsourced dataset statistics are kept with [CONFIRM]; the weight_kg clock caveat stated as a limitation with no ablation; Logistic Regression and GBT added - **Second pass:** the two dataset statistics were re-computed from the Silver Parquet and their [CONFIRM] tags removed (3b, 5b).
- **2.6 Implementation table (Table 13):** Repository row names the E1 and E2 scripts instead of models/spark_report_classification.py
- **3.5 Inference:** New: Table 19 (use of each result), derived-data caveat, one-seed limitation, verification paragraph incl. the defective E2 check
- **Section 3 (new):** 3. USER-LEVEL AND ACTIVITY-LEVEL CLASSIFICATION (E3, E4): 3.1-3.6, Tables 14-20, Listings 5-8 (verbatim excerpts of models/sup_e3_user_high_achiever.py and sup_e4_activity_level.py, long lines wrapped), Figure 3 (ROC AUC chart drawn from the CSVs)
- **Title page:** 'Classification & Clustering Analysis' -> 'Supervised Learning Analysis (Experiments E1 to E5)'
- **Figure 1 (picture):** The embedded picture contained the text 'Predictions / Clusters' and 'RF, K-Means, LR'; redrawn in the same style as 'Predictions / Results' and 'Supervised E1 to E5'
- **Table of contents (cached entries):** Entries 2 and 3 renamed; page numbers refreshed from a Word render (see build log)
- **Package clean-up:** the three embedded K-Means images were dropped from the file; Figure 1's picture was redrawn (it contained the text 'Predictions / Clusters' and 'RF, K-Means, LR'); a new chart (Figure 3) was drawn from the CSVs; the TOC page numbers were refreshed from a Word render.

### Deck v2

- **Slide 2 (Contents):** Entry 9 renamed 'Other Experiments: E3, E4 and E5'
- **Slide 4 + its speaker notes:** K-Means box replaced by the E3/E4 supervised classifiers (no reliable skill, ROC-AUC ranges from the CSVs); notes rewritten
- **Slide 5 (architecture):** 'Predictions & Clusters' -> 'Predictions & Results'; model list 'RF · K-Means · Linear Regression' -> 'RF · Logistic Reg. · GBT · Linear Regression'
- **Slide 6 + notes:** K-Means removed from the standardisation step; split step names the protocol of each experiment
- **Slide 8 + notes:** Unconfirmed tuning-grid statements kept but tagged [CONFIRM]; validation AUC 0.7549 re-read from E1_results.csv - **Second pass:** the three [CONFIRM] tags on the slide and the one in the notes were replaced by the confirmed grid (3b, 5b).
- **Slide 9 + notes:** Weighted precision/recall rows (not in the results CSV) replaced by F1 macro and the baseline accuracy; remaining table values verified against E1_results.csv; weight_kg caution rewritten (calendar clock, no ablation) with the unsourced 'weight rises while steps fall' removed
- **Slide 10 (+ chart, table, notes):** Rebuilt for E1 (three models) and E2 (chronological test, weak) against their baselines; chart and 9-row table re-read from the CSVs; scope note rewritten (old note said Logistic Regression was not part of the figures)
- **Slide 11 (rebuilt):** Title 'Other Experiments: E3, E4 and E5 (supervised)'; left panel now E3/E4 supervised results (3 tiles, 4-row table, 'No reliable skill' note); right panel E5 kept (LR values verified) with the tree regressors and the formula-recovery caveat; footnote now states E2 is weak
- **Slide 12 (the 'Done' row) + notes:** 'RF, K-Means, Linear Regression: Done' -> 'E1-E5: RF, Logistic, GBT, regression: Done'; 'better segmentation' removed; notes say five supervised experiments
- **Slide 13:** Page tile 'User Segmentation' -> 'Supervised Results'; small print states CSV exports (not HDFS) and carries a [CONFIRM] about the .pbix re-save; no claim that the dashboard shows E1-E5 - **Third pass:** the old screenshot was removed and replaced by a placeholder text box (3c); the small print and its [CONFIRM] are unchanged.
- **Slide 14 (picture):** The web-page screenshot showed the removed 'YOUR ACTIVITY GROUP / K-Means grouping' card; replaced by a fresh screenshot of the current page (webapp/public served locally, user 1503, headless Edge), cropped to the top part
- **Slide 14:** K-Means (activity group) removed from the web-page model list; the ROC-AUC 0.755 was first kept with [CONFIRM] and then DELETED in the second pass (3b)
- **Slide 15 + notes:** Removed the four K-Means references (MacQueen, k-means++, scalable k-means++, silhouette) and renumbered [1]-[7]; no slide cites a reference by number; notes updated
- **Slide 16 (table):** Rows 'Classification script', 'K-Means script' and 'Calorie model script' replaced by the E1/E2, E3/E4 and E5 script paths
- **Slide mapping (agreed with 'go'):** 'Other Experiments' is slide 11 (not 16), the K-Means 'Done' row is on slide 12 (not 11), the K-Means script row is on slide 16, slide 14 has no speaker notes; notes were edited on slides 4, 6, 8, 9, 10, 12 and 15.

### ML-part guide

- **Whole document:** Recomposed on a copy of the original (same styles, callouts, tables, header and footer; footer date set to 26 October 2026), 25 pages, 36 questions. The old text described two K-Means experiments, the old Random Forest and calorie numbers and an old tuning grid, so it was rewritten rather than patched.
- **Section 1:** At a glance: five supervised experiments, the plain headline (E1 clearly above baseline, E2 weak, E3 and E4 no reliable skill, E5 largely formula recovery), the stage table, the five-experiment table and a new Golden rule.
- **Section 2:** 2.1 data, 2.2 framing and leakage rules, 2.3 splits, 2.4 one block per experiment with its table, 2.5 metrics in plain English, 2.6 verification (all 17 leakage runs, the cross-check with its kind-by-kind table, the defective E2 check as two separate facts with cause and cross-link, local vs HDFS, reproduction), 2.7 hand-off, 2.8 the two open items (E1 edit UNCONFIRMED, E5 regeneration UNKNOWN).
- **Sections 3 and 4:** Nine limitations; 36 questions in nine groups (big picture, data and splitting, E1 to E5, verification and honesty, cross-questions), each with an evidence tag.
- **Appendices B to E:** New numbers cheat-sheet, file map, re-run commands (usage lines read from run_supervised.ps1 and the script headers) and 'What you must not claim'.
- **Appendix A:** Copied unchanged from the original, with an amber note and a [CONFIRM] (its upstream numbers were not re-checked). - **Second pass:** its numbers were re-checked (5b) and the [CONFIRM] removed; the note now reads 'Upstream stages. The numbers in this appendix were re-checked against the data files and the HDFS evidence.'

### Member-contributions review

- **Section 2 (Abhirami), whole section:** Removed and rewritten for the supervised experiments E1-E5 (the old section described two K-Means experiments, the old Random Forest numbers and an old grid)
- **Section 2 (Abhirami), new content:** Rewritten: what was done, five experiments table, key files, verification (leakage runs, cross-check, the defective E2 check as two facts, local vs HDFS, reproduction), two open items (UNCONFIRMED E1 edit, UNKNOWN E5 regeneration), limits incl. the derived-data caveat, 9 likely questions, 30-second version
- **Opening paragraph:** Sourcing statement made true for the rewritten Abhirami section
- **At a glance table:** Abhirami row rewritten for E1-E5; Mahendran row: '70 visuals' removed (the previous file's count)
- **Prajin: 'How it was verified' (ML re-run bullet), limits bullet on where notebook sections ran, evidence-folder row:** The old K-Means/Random Forest re-run comparison file is archived; replaced by the E1-E5 local-vs-HDFS comparison (485 rows, 0 flagged); numbers from local_vs_hdfs_comparison.csv
- **Mahendran: data layer, model and report, five pages, web-page description/models/validation, key-files rows, verification and limits bullets, one likely question:** K-Means/segment/silhouette content removed or replaced by the supervised pages of the regenerated project; old visual/measure/slicer/check counts removed; the saved .pbix re-save is flagged with [CONFIRM]
- **Section 4 hand-offs (data flow) and section 5 git table / 'not committed' paragraph:** Updated for E1-E5 (no 'segment models', no report-aligned E1/E3 scripts); the second commit is described as the earlier notebook version

## 3b. Second pass (27 Oct 2026): edits made after the [CONFIRM] review

Approved choices: items 2, 3, 4, 5, 9 applied as proposed; the 0.755 figure deleted without replacement (deck slide 14 and the member review); the four items that wait for the `.pbix` re-save (Report Table 2, deck slide 13 text, deck slide 13 picture, member review 'Power BI') left exactly as they were, with their tags, no interim wording and no new screenshot. The old slide 13 screenshot was still in the deck, unaltered, at the end of the second pass; the third pass removed it (3c). Each edit below is a run-level text replacement; layout and formatting were not touched.

- **Report 2.2 hyperparameters.** Old: "[CONFIRM: the earlier statement that numTrees 50 and 100 and maxDepth 5, 10, 15 and 20 were searched, with two combinations lost to an out-of-memory error and a validation AUC of 0.7269 at maxDepth = 5, is not in the saved evidence]" New: "This setting comes from an earlier search that E1 reuses: numTrees 50 and 100 with maxDepth 5, 10, 15 and 20 were tried and the best validation ROC AUC was kept. With 50 trees the validation ROC AUC was 0.7269 at maxDepth 5, 0.7492 at 10, 0.7549 at 15 and 0.7541 at 20; with 100 trees it was 0.7294 at 5 and 0.7544 at 10. The two combinations with 100 trees at maxDepth 15 and 20 ran out of memory and were not run."
- **Report 2.5 weight.** Old: "(by about 59 kg between the lightest and heaviest day [CONFIRM], an implausibly large change that suggests simulated data)" New: "(by about 59 kg between a user's lightest and heaviest day, with a median of 58.8 kg over the 437 users, an implausibly large change that suggests simulated data)"
- **Report 2.5 steps.** Old: "to about 7,400 in the second [CONFIRM]." New: "to about 7,400 in the second (averages of 9,574 and 7,373 steps per user-day)."
- **Guide Appendix A note.** Old: "Carried over unchanged.  This appendix is kept as it was in the earlier version of this guide. Its numbers describe the upstream stages and were not re-read from the result files for this version. [CONFIRM]" New: "Upstream stages.  The numbers in this appendix were re-checked against the data files and the HDFS evidence."
- **Member review 'Models behind it'.** Old: "Logistic Regression (next-day goal probability, ROC-AUC 0.755 [CONFIRM]) and Linear Regression" New: "Logistic Regression (next-day goal probability) and Linear Regression"
- **Member review 'Web page'.** Old: ", and that the Logistic Regression re-measured on the held-out period still gives ROC-AUC 0.755." New: "."
- **Member review 'Unassigned model code'.** Old: "the web page's tomorrow probability, ROC-AUC 0.755)" New: "the web page's tomorrow probability)"
- **Deck slide 8 table, Tuning grid.** Old: "trees {50,100} × depth {5,10,15,20} [CONFIRM]" New: "trees {50,100} × depth {5,10,15,20}"
- **Deck slide 8 table, Not run.** Old: "100 trees at depth 15, 20 (out of memory) [CONFIRM]" New: "100 trees at depth 15, 20 (out of memory)"
- **Deck slide 8 AUC line.** Old: "Validation AUC: 0.7549 at depth 15 vs 0.7269 at depth 5 [CONFIRM]." New: "Validation AUC (50 trees): 0.7549 at depth 15 vs 0.7269 at depth 5."
- **Deck slide 8 notes.** Old: "[CONFIRM: the earlier note said trees 50 and 100 and depth 5, 10, 15, 20 were tuned and that two settings ran out of memory; that grid is not in the saved evidence.]" New: "The setting comes from an earlier search that E1 reuses: trees 50 and 100 with depth 5, 10, 15 and 20, the best validation ROC-AUC kept. The two settings with 100 trees at depth 15 and 20 ran out of memory and were not run."
- **Deck slide 14 'Web page models'.** Old: "Logistic Regression (next-day goal probability, ROC-AUC 0.755 [CONFIRM]) and Linear Regression" New: "Logistic Regression (next-day goal probability) and Linear Regression"

Checks after the edits: the skill validators pass for all four files; the Report TOC page numbers were re-compared with a fresh Word render and did not change (22 pages); numbering of tables, figures and listings and all cross-references were re-checked by script; the pages and slides that contain edits (Report pages 9, 10, 15; deck slides 8 and 14; guide page 20; member review pages 8 to 10) were looked at as images; a scan of every XML part and of the rendered PDF text found no K-Means, silhouette, unsupervised, PCA, elbow, Isolation Forest, 34.44, 0.3528, 0.3413, 45,306, 54,816, 228, 209, 0.2018 or 0.755. The word 'cluster' remains only for HDFS and Spark clusters and the MapReduce paper title. The words 'segment', 'segmentation' and 'anomaly' remain only in the guide and the member review, in sentences that say the earlier experiments were replaced or that the web page has no such section.

## 3c. Third pass (27 Oct 2026): slide 13 screenshot and the stale PDF

- **Deck slide 13, picture.** The picture 'Picture 6' (the Power BI Fitness Overview screenshot of the OLD `.pbix`, showing the 'User segment (E3)' slicer and the 'User Segmentation' tab) was removed from the slide. Its bytes were copied, unchanged, to `D:\bigdata\archive\slide13_powerbi_screenshot_OLD_pbix_removed_from_final_fitpulseppt_v2_supervised.png` (162,102 bytes, SHA-256 `057E528A33CCB4C28748A535892F9D137871EA3229AA9370D7082DB1C7FDDE57`); that folder did not exist and was created next to the deck. The embedded copy inside the deck was dropped with the picture (the original deck `final_fitpulseppt_v2.pptx` still holds the same image).
- **Deck slide 13, placeholder.** A visible text box named 'Screenshot placeholder' now sits at the picture's position and size (x 457200, y 1280160, w 5120640, h 3429578 EMU, same place in the stacking order): light amber fill, dashed amber outline, centred bold 18 pt text '[SCREENSHOT PENDING: Power BI Fitness Overview after re-save]'. Nothing else on the slide was changed: the caption 'Fitness Overview page (1 of 5 pages)', the five page tiles, the small print with its [CONFIRM] and the four insight cards are as before.
- **Checks.** The skill validator passes. A part-by-part comparison with the deck before the edit shows that only `ppt/slides/slide13.xml`, `ppt/slides/_rels/slide13.xml.rels` and the removed `ppt/media/image2.png` differ (the other 15 slides are byte-identical). The deck was re-rendered by PowerPoint (16 pages) and slide 13 was looked at as an image; a scan of every XML part and of the rendered text found no K-Means, silhouette, unsupervised, segment, PCA, elbow, Isolation Forest, 34.44, 0.3528, 0.3413, 45,306, 54,816, 228, 209, 0.2018 or 0.755; the only [CONFIRM] left in the deck is the slide 13 small print; the media folder now holds only the logo and the two slide 14 screenshots.
- **Stale PDF renamed.** `D:\bigdata\final_fitpulseppt_v2_supervised.pdf` was renamed to `D:\bigdata\final_fitpulseppt_v2_supervised_STALE_do_not_use.pdf` (move within the same folder; 635,317 bytes, SHA-256 `7DCA5888D24BBDE0415C0FE575FBF521E95E7DBA630E4570AB9012ADBA308F3A` before and after). No new PDF was exported. `D:\bigdata\final_fitpulseppt_v2.pdf` (old deck, 14 Oct) was not touched.

## 4. Every [CONFIRM] and open item

**Four [CONFIRM] tags remain in the documents** (Report Table 2; deck slide 13 text; member review: one in 'What was done: Power BI' and one in the key-files table), plus the visible placeholder '[SCREENSHOT PENDING: Power BI Fitness Overview after re-save]' that now stands where the old screenshot was on deck slide 13. All of them wait for the `.pbix` re-save. The other seven items were resolved on 27 Oct 2026 and are listed in the table after the next one.

| Document | Where | What must be confirmed or done |
|---|---|---|
| Report v3 | Table 2, Power BI row | The saved .pbix is still the previous version until it is re-saved in Power BI Desktop; do not claim it shows E1-E5 yet |
| Deck v2 | Slide 13 | Page-name tile 'Supervised Results' and the supervised pages exist only in the regenerated project until the .pbix is re-saved in Power BI Desktop; no E1-E5 claim is made |
| Deck v2 | Slide 13 picture (now a placeholder) | The old screenshot (of the OLD .pbix, with the 'User segment (E3)' slicer and the 'User Segmentation' tab) was removed on 27 Oct 2026 and archived; the placeholder '[SCREENSHOT PENDING: Power BI Fitness Overview after re-save]' stays until a new screenshot is taken after the .pbix is re-saved (powerbi/capture_powerbi_screenshots.ps1) |
| Member-contributions review | Mahendran 'What was done: Power BI' (model and report) | The saved .pbix still has to be re-saved; the previous counts (70 visuals, 34 measures, 15 slicers, 70 project checks) no longer describe the regenerated project and were removed rather than re-counted |

Resolved on 27 Oct 2026 (the tags and the 0.755 figure no longer appear in the documents):

| # | Document and place | Result | Source (and exact query) | What was done |
|---|---|---|---|---|
| 2 | Report 2.2, Random Forest grid | Confirmed | `faculty_evidence/report_aligned/rf_tuning_grid.csv` (8 rows: numTrees, maxDepth, validation_ROC_AUC, seconds, status) and `faculty_evidence/log_report_rf_hdfs_attempt1_full_grid.txt` (50 trees at depth 5 = 0.7269165599743449 on line 15; java.lang.OutOfMemoryError from line 30, stage 636). Selected setting read from `faculty_evidence/report_aligned/rf_run_info.json` (numTrees 50, maxDepth 15), which `models/sup_e1_goal_same_day.py` reads (header lines 5-6, line 62). Cross-check: `exports/E1_results.csv` Random Forest ROC AUC validation = 0.754869 against 0.754868 in the grid. These two files are outside `exports/` and `faculty_evidence/supervised/`; their use as a source was accepted on 27 Oct 2026. | [CONFIRM] replaced by the grid values (3b, 5b) |
| 5 | Deck slide 8 (table, AUC line, notes) | Confirmed | Same files as item 2. | Three tags and the notes bracket removed; the AUC line now says '(50 trees)' |
| 3 | Report 2.5, 'about 59 kg' | Confirmed | Computed from the Silver Parquet, query in 5b: per-user (max - min) of weight_kg over 437 users: median 58.80 kg, mean 58.79 kg, range 53.10 to 67.00 kg | Tag removed; 'a user's lightest and heaviest day' and 'median of 58.8 kg over the 437 users' added |
| 4 | Report 2.5, 'about 9,600 to about 7,400' | Confirmed | Computed from the Silver Parquet, query in 5b: mean steps per user-day January to June 9,574.2 (56,937 rows), July to December 7,373.0 (43,185 rows) | Tag removed; '(averages of 9,574 and 7,373 steps per user-day)' added |
| 9 | Guide, Appendix A | Confirmed (every number re-checked) | Table in 5b: Kaggle file, Bronze, Silver and `faculty_evidence/hdfs/` files, computed or read as listed | Tag removed; the note now says the numbers were re-checked against the data files and the HDFS evidence |
| 8 | Deck slide 14, ROC-AUC 0.755 | Confirmed by recomputation (0.7546 on 9,760 rows), but not used | A recomputation of the saved legacy model was done read-only for the review (scratch script `work/legacy_auc.py`); not used in any document | The figure and its tag were DELETED, not replaced, as instructed |
| 11 | Member review, ROC-AUC 0.755 (three places: 'Models behind it', 'Web page', 'Unassigned model code') | Same as item 8 | Same as item 8 | The figure was deleted in all three places; in 'Web page' the clause about re-measuring the Logistic Regression was cut, so the sentence now ends after the 437 'tomorrow' probabilities |

Other things that need you (not tagged in the documents):

1. **Re-save the `.pbix`** from `powerbi/project/FitPulse_PowerBI_Dashboard.pbip` in Power BI Desktop, then tell me; the deck (slide 13 text and its screenshot placeholder), the Report (Table 2 note) and the member review can then drop their [CONFIRM] notes and say the dashboard shows the supervised results.
2. **Slide 13 screenshot is pending.** The old screenshot was removed from slide 13 and archived as `D:\bigdata\archive\slide13_powerbi_screenshot_OLD_pbix_removed_from_final_fitpulseppt_v2_supervised.png`; a placeholder text box stands in its place. After the re-save, take the new Fitness Overview screenshot (`powerbi/capture_powerbi_screenshots.ps1`) and replace the placeholder; tell me and I will do it and re-render.
3. **Deck PDF.** The draft PDF exported on 27 Oct 2026 before the second pass is now `D:\bigdata\final_fitpulseppt_v2_supervised_STALE_do_not_use.pdf` (renamed, content unchanged, SHA-256 `7DCA5888D24BBDE0415C0FE575FBF521E95E7DBA630E4570AB9012ADBA308F3A`); it shows the old slide 8 tags, the 0.755 figure and the old slide 13 screenshot and must not be used. `D:\bigdata\final_fitpulseppt_v2.pdf` is the PDF of the old deck and was not touched. No new PDF has been exported (instruction: not yet); export one from `final_fitpulseppt_v2_supervised.pptx` after the `.pbix` re-save and the new screenshot.
4. **Pre-existing, not changed:** the 'Fault tolerance' bullet in Report section 1.6 is entirely bold in the original too.
5. **A hidden Word process** (id 17672, started 26 Oct 22:23, no window) is still running on this machine. It is probably left over from my first failed render attempt, but I could not prove it was mine, so I did not stop it. All later renders used private Office instances.

## 5. Numbers I wrote or changed, with their source

### Report v3 (151 entries)

| Where | Value shown | Source | Also in SUPERVISED_REPORT.md |
|---|---|---|---|
| 1.1 E5 LR MAE | 199.71 | exports/E5_results.csv \| Linear Regression \| MAE (kcal) \| test | yes |
| 1.1 E5 LR RMSE | 263.64 | exports/E5_results.csv \| Linear Regression \| RMSE (kcal) \| test | yes |
| 1.1 E5 LR R2 | 0.6296 | exports/E5_results.csv \| Linear Regression \| R2 \| test | yes |
| 1.1 E5 baseline MAE | 334.51 | exports/E5_results.csv \| Baseline: training mean \| MAE (kcal) \| test | yes |
| 2.1 E2 split rows train | 50,014 | faculty_evidence/supervised/E2_split_summary.csv (rows) | yes |
| 2.1 E2 split rows validation | 6,513 | faculty_evidence/supervised/E2_split_summary.csv (rows) | yes |
| 2.1 E2 split rows test | 7,647 | faculty_evidence/supervised/E2_split_summary.csv (rows) | yes |
| 2.1 E2 cut dates | 2024-09-08 / 2024-11-02 | faculty_evidence/supervised/E2_split_summary.csv (cut_train_end, cut_validation_end) | no |
| Table 5 E2 feature count | 20 | faculty_evidence/supervised/final_feature_set_E1_E5.csv (20 non-target rows for E2) | yes |
| 2.1 leakage accuracy (unchanged text, verified) | 98.95% | exports/E1_results.csv \| Random Forest + steps & distance_km (LEAKAGE) \| Accuracy \| test \| INVALID | no |
| 2.2 RF validation AUC | 0.7549 | exports/E1_results.csv \| Random Forest \| ROC AUC \| validation | no |
| 2.2 LR grid | reg 0.0, 0.01, 0.1, 1.0; best reg 0.0 | faculty_evidence/supervised/E1_tuning_grid.csv | no |
| 2.2 GBT grid | depth 3, 5; iterations 50, 100; best depth 5, 100 iterations | faculty_evidence/supervised/E1_tuning_grid.csv | no |
| 2.3 E1 reproduction | 1.6e-06 | faculty_evidence/supervised/E1_reproduction_check.csv (max abs_diff over 14 rows) | no |
| 2.4 E1 local vs HDFS | 9.36e-06 | faculty_evidence/supervised/local_vs_hdfs_comparison.csv (E1 rows, status VALID/BASELINE: 60 rows) | yes |
| Table 8 validation Accuracy | 0.7293 | exports/E1_results.csv \| Random Forest \| Accuracy \| validation | no |
| Table 8 test Accuracy | 0.7352 | exports/E1_results.csv \| Random Forest \| Accuracy \| test | yes |
| Table 8 validation Precision (goal-achieved class) | 0.7708 | exports/E1_results.csv \| Random Forest \| Precision (positive class) \| validation | no |
| Table 8 test Precision (goal-achieved class) | 0.7801 | exports/E1_results.csv \| Random Forest \| Precision (positive class) \| test | no |
| Table 8 validation Recall (goal-achieved class) | 0.7912 | exports/E1_results.csv \| Random Forest \| Recall (positive class) \| validation | no |
| Table 8 test Recall (goal-achieved class) | 0.7923 | exports/E1_results.csv \| Random Forest \| Recall (positive class) \| test | no |
| Table 8 validation F1-Score (goal-achieved class) | 0.7809 | exports/E1_results.csv \| Random Forest \| F1 (positive class) \| validation | no |
| Table 8 test F1-Score (goal-achieved class) | 0.7862 | exports/E1_results.csv \| Random Forest \| F1 (positive class) \| test | no |
| Table 8 validation F1-Score (weighted) | 0.7282 | exports/E1_results.csv \| Random Forest \| F1 (weighted) \| validation | no |
| Table 8 test F1-Score (weighted) | 0.7346 | exports/E1_results.csv \| Random Forest \| F1 (weighted) \| test | yes |
| Table 8 validation F1-Score (macro) | 0.7134 | exports/E1_results.csv \| Random Forest \| F1 (macro) \| validation | no |
| Table 8 test F1-Score (macro) | 0.7193 | exports/E1_results.csv \| Random Forest \| F1 (macro) \| test | no |
| Table 8 validation ROC AUC | 0.7549 | exports/E1_results.csv \| Random Forest \| ROC AUC \| validation | no |
| Table 8 test ROC AUC | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| Table 8 validation Baseline accuracy (always predict majority class) | 0.6096 | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| validation | no |
| Table 8 test Baseline accuracy (always predict majority class) | 0.6144 | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| test | yes |
| Table 9 (verified, unchanged) TN | 3,676 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Table 9 (verified, unchanged) FP | 2,030 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Table 9 (verified, unchanged) FN | 1,888 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Table 9 (verified, unchanged) TP | 7,202 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Table 10 (verified, unchanged) weight_kg | 0.2822 | exports/E1_feature_importance.csv \| Random Forest \| importance | no |
| Table 10 (verified, unchanged) bmi | 0.0929 | exports/E1_feature_importance.csv \| Random Forest \| importance | no |
| Table 10 (verified, unchanged) height_cm | 0.0601 | exports/E1_feature_importance.csv \| Random Forest \| importance | no |
| Table 10 (verified, unchanged) activity_type | 0.0586 | exports/E1_feature_importance.csv \| Random Forest \| importance | no |
| Table 10 (verified, unchanged) active_minutes | 0.0480 | exports/E1_feature_importance.csv \| Random Forest \| importance | no |
| Table 11 E1, random split, test Random Forest accuracy | 0.7352 | exports/E1_results.csv \| Random Forest \| Accuracy \| test | yes |
| Table 11 E1, random split, test Random Forest AUC | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| Table 11 E1, random split, test Logistic Regression accuracy | 0.7356 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test | yes |
| Table 11 E1, random split, test Logistic Regression AUC | 0.7396 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test | yes |
| Table 11 E1, random split, test Gradient-Boosted Trees accuracy | 0.7382 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test | yes |
| Table 11 E1, random split, test Gradient-Boosted Trees AUC | 0.7735 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test | yes |
| Table 11 E1, random split, test baseline | 0.6144 | exports/E1_results.csv \| Baseline accuracy (always majority class) \| test (identical in all model rows) | yes |
| Table 11 E1, user-held-out test Random Forest accuracy | 0.7232 | exports/E1_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| Table 11 E1, user-held-out test Random Forest AUC | 0.7498 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| Table 11 E1, user-held-out test Logistic Regression accuracy | 0.7315 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test (user-held-out) | yes |
| Table 11 E1, user-held-out test Logistic Regression AUC | 0.7340 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test (user-held-out) | yes |
| Table 11 E1, user-held-out test Gradient-Boosted Trees accuracy | 0.7224 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test (user-held-out) | yes |
| Table 11 E1, user-held-out test Gradient-Boosted Trees AUC | 0.7608 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| Table 11 E1, user-held-out test baseline | 0.6168 | exports/E1_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| Table 11 E2, chronological test Random Forest accuracy | 0.5823 | exports/E2_results.csv \| Random Forest \| Accuracy \| chronological test | yes |
| Table 11 E2, chronological test Random Forest AUC | 0.6706 | exports/E2_results.csv \| Random Forest \| ROC AUC \| chronological test | yes |
| Table 11 E2, chronological test Logistic Regression accuracy | 0.6835 | exports/E2_results.csv \| Logistic Regression \| Accuracy \| chronological test | yes |
| Table 11 E2, chronological test Logistic Regression AUC | 0.7004 | exports/E2_results.csv \| Logistic Regression \| ROC AUC \| chronological test | yes |
| Table 11 E2, chronological test Gradient-Boosted Trees accuracy | 0.5991 | exports/E2_results.csv \| Gradient-Boosted Trees \| Accuracy \| chronological test | yes |
| Table 11 E2, chronological test Gradient-Boosted Trees AUC | 0.6970 | exports/E2_results.csv \| Gradient-Boosted Trees \| ROC AUC \| chronological test | yes |
| Table 11 E2, chronological test baseline | 0.5886 | exports/E2_results.csv \| Baseline accuracy (always majority class) \| chronological test (identical in all model rows) | yes |
| Table 11 E2 training-majority baseline | 0.4114 | exports/E2_results.csv \| Random Forest \| Baseline accuracy (always TRAINING-majority class) \| chronological test | yes |
| 2.4 E2 text accuracy | 0.5823 | exports/E2_results.csv \| Random Forest \| Accuracy \| chronological test | yes |
| 2.4 E2 text accuracy | 0.6835 | exports/E2_results.csv \| Logistic Regression \| Accuracy \| chronological test | yes |
| 2.4 E2 text accuracy | 0.5991 | exports/E2_results.csv \| Gradient-Boosted Trees \| Accuracy \| chronological test | yes |
| 2.4 E2 text AUC | 0.6706 | exports/E2_results.csv \| Random Forest \| ROC AUC \| chronological test | yes |
| 2.4 E2 text AUC | 0.7004 | exports/E2_results.csv \| Logistic Regression \| ROC AUC \| chronological test | yes |
| 2.4 E2 text AUC | 0.6970 | exports/E2_results.csv \| Gradient-Boosted Trees \| ROC AUC \| chronological test | yes |
| 2.4 E2 text baseline | 0.5886 | exports/E2_results.csv \| Baseline accuracy (always majority class) \| chronological test (identical in all model rows) | yes |
| 2.4 E2 goal rate train | 0.7378 | faculty_evidence/supervised/E2_split_summary.csv (positive_share) | yes |
| 2.4 E2 goal rate validation | 0.2246 | faculty_evidence/supervised/E2_split_summary.csv (positive_share) | yes |
| 2.4 E2 goal rate test | 0.4114 | faculty_evidence/supervised/E2_split_summary.csv (positive_share) | yes |
| 2.4 E2 random-split AUC (reference) | 0.8191 | exports/E2_results.csv \| Random Forest \| ROC AUC \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E2 random-split AUC (reference) | 0.8295 | exports/E2_results.csv \| Logistic Regression \| ROC AUC \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E2 random-split AUC (reference) | 0.8301 | exports/E2_results.csv \| Gradient-Boosted Trees \| ROC AUC \| random split (NOT headline) \| REFERENCE | yes |
| 2.5 E1 accuracy gap (pp) | 12.1 | derived: E1 RF test accuracy minus baseline (exports/E1_results.csv) | yes |
| 2.5 E1 recall of the missed class | 64.4% (3,676 of 5,706) | derived from predictions/E1_Random_Forest_test.csv | no |
| 2.5 acc % | 73.5% | exports/E1_results.csv \| Random Forest \| Accuracy \| test | no |
| 2.5 baseline % | 61.4% | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| test | no |
| 2.5 AUC | 0.759 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | no |
| 2.5 recall % | 79.2% | exports/E1_results.csv \| Random Forest \| Recall (positive class) \| test | no |
| 2.5 precision % | 78.0% | exports/E1_results.csv \| Random Forest \| Precision (positive class) \| test | no |
| 2.5 user-held-out acc % | 72.3% | exports/E1_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | no |
| 2.5 user-held-out AUC | 0.750 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| 2.5 LR acc | 0.7356 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test | yes |
| 2.5 GBT acc | 0.7382 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test | yes |
| 2.5 LR AUC | 0.7396 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test | yes |
| 2.5 GBT AUC | 0.7735 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test | yes |
| 3.1 E3 users | 437 | SUPERVISED_REPORT.md section 2 (E3: 437 users, 218 high achievers) | yes |
| 3.1 E3 high achievers | 218 | SUPERVISED_REPORT.md section 2 (E3: 437 users, 218 high achievers) | yes |
| 3.1 E4 train users | 312 | SUPERVISED_REPORT.md section 2 (E4 users) / faculty_evidence/supervised/predictions/E4_splits.csv | yes |
| 3.1 E4 validation users | 72 | SUPERVISED_REPORT.md section 2 (E4 users) / faculty_evidence/supervised/predictions/E4_splits.csv | yes |
| 3.1 E4 test users | 53 | SUPERVISED_REPORT.md section 2 (E4 users) / faculty_evidence/supervised/predictions/E4_splits.csv | yes |
| Table 14 feature counts | 9 (E3) and 16 (E4) | faculty_evidence/supervised/final_feature_set_E1_E5.csv | no |
| Table 16 Random Forest accuracy | 0.5355 | exports/E3_results.csv \| Random Forest \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Random Forest F1w | 0.5318 | exports/E3_results.csv \| Random Forest \| F1 (weighted) \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Random Forest AUC | 0.5425 | exports/E3_results.csv \| Random Forest \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Random Forest AUC fold mean | 0.5446 | exports/E3_results.csv \| Random Forest \| ROC AUC (mean over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Random Forest AUC fold sd | 0.0377 | exports/E3_results.csv \| Random Forest \| ROC AUC (sd over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Logistic Regression accuracy | 0.5378 | exports/E3_results.csv \| Logistic Regression \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Logistic Regression F1w | 0.5361 | exports/E3_results.csv \| Logistic Regression \| F1 (weighted) \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Logistic Regression AUC | 0.5486 | exports/E3_results.csv \| Logistic Regression \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Logistic Regression AUC fold mean | 0.5725 | exports/E3_results.csv \| Logistic Regression \| ROC AUC (mean over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 Logistic Regression AUC fold sd | 0.0332 | exports/E3_results.csv \| Logistic Regression \| ROC AUC (sd over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| Table 16 baseline | 0.5011 | exports/E3_results.csv \| Baseline accuracy (always majority class) \| stratified 5-fold CV (out-of-fold) (identical in all model rows) | yes |
| 3.4 E3 gap over baseline (pp) | 3.4 to 3.7 | derived: E3 accuracy minus baseline (exports/E3_results.csv) | no |
| 3.4 text RF acc | 0.5355 | exports/E3_results.csv \| Random Forest \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| 3.4 text LR acc | 0.5378 | exports/E3_results.csv \| Logistic Regression \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| 3.4 text baseline | 0.5011 | exports/E3_results.csv \| Baseline accuracy (always majority class) \| stratified 5-fold CV (out-of-fold) (identical in all model rows) | yes |
| 3.4 text RF AUC | 0.5425 | exports/E3_results.csv \| Random Forest \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
| 3.4 text LR AUC | 0.5486 | exports/E3_results.csv \| Logistic Regression \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
| 3.4 text RF sd | 0.0377 | exports/E3_results.csv \| Random Forest \| ROC AUC (sd over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| 3.4 text LR sd | 0.0332 | exports/E3_results.csv \| Logistic Regression \| ROC AUC (sd over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| 3.4 coverage-only RF AUC | 0.6077 | exports/E3_results.csv \| Random Forest: logging-window coverage ONLY (mean logged month) \| ROC AUC \| stratified 5-fold CV (out-of-fold) \| REFERENCE | yes |
| 3.4 coverage-only LR AUC | 0.6195 | exports/E3_results.csv \| Logistic Regression: logging-window coverage ONLY (mean logged month) \| ROC AUC \| stratified 5-fold CV (out-of-fold) \| REFERENCE | yes |
| 3.4 standard error of an accuracy (437 users) | about 2.4 percentage points | SUPERVISED_REPORT.md section 3.3 (derived: sqrt(p(1-p)/n)) | yes |
| Table 17 Random Forest acc | 0.5056 | exports/E4_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| Table 17 Random Forest F1m | 0.4406 | exports/E4_results.csv \| Random Forest \| F1 (macro) \| test (user-held-out) | yes |
| Table 17 Random Forest AUC | 0.4965 | exports/E4_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| Table 17 Logistic Regression acc | 0.5040 | exports/E4_results.csv \| Logistic Regression \| Accuracy \| test (user-held-out) | yes |
| Table 17 Logistic Regression F1m | 0.4442 | exports/E4_results.csv \| Logistic Regression \| F1 (macro) \| test (user-held-out) | yes |
| Table 17 Logistic Regression AUC | 0.4999 | exports/E4_results.csv \| Logistic Regression \| ROC AUC \| test (user-held-out) | yes |
| Table 17 Gradient-Boosted Trees acc | 0.5036 | exports/E4_results.csv \| Gradient-Boosted Trees \| Accuracy \| test (user-held-out) | yes |
| Table 17 Gradient-Boosted Trees F1m | 0.5002 | exports/E4_results.csv \| Gradient-Boosted Trees \| F1 (macro) \| test (user-held-out) | yes |
| Table 17 Gradient-Boosted Trees AUC | 0.4999 | exports/E4_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| Table 17 baseline | 0.5079 | exports/E4_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| 3.4 E4 baseline | 0.5079 | exports/E4_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| 3.4 E4 AUC range | 0.4965 to 0.4999 | exports/E4_results.csv \| ROC AUC \| test (user-held-out) | no |
| 3.4 E4 accuracy range | 0.5036 to 0.5056 | exports/E4_results.csv \| Accuracy \| test (user-held-out) | no |
| Table 18 E1 | 0.9996 to 1.0000 \| 0.7396 to 0.7735 | exports/E1_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| Table 18 E2 | 0.7518 to 0.8787 \| 0.6706 to 0.7004 | exports/E2_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| Table 18 E3 | 0.7978 to 0.8242 \| 0.5425 to 0.5486 | exports/E3_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| Table 18 E4 | 0.8905 to 0.9976 \| 0.4965 to 0.4999 | exports/E4_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| Table 18 E5 | 0.7032 to 0.7450 \| 0.6296 to 0.6658 | exports/E5_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| 3.4 leakage runs | 17 | exports/E1..E5_results.csv (rows with status INVALID and metric ROC AUC / R2) | yes |
| 3.4 E4 without leak AUC | 0.4999 | exports/E4_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| 3.5 E1 baseline | 0.6144 | exports/E1_results.csv \| Baseline accuracy (always majority class) \| test (identical in all model rows) | yes |
| 3.5 E5 baseline MAE | 334.51 | exports/E5_results.csv \| Baseline: training mean \| MAE (kcal) \| test | yes |
| 3.5 E1 accuracy range | 0.7352 to 0.7382 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 3.5 E1 AUC range | 0.7396 to 0.7735 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 3.5 E2 AUC range | 0.6706 to 0.7004 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 3.5 E3 AUC range | 0.5425 to 0.5486 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 3.5 E5 MAE range | 183.28 to 199.71 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 3.5 E5 formula-recovery R2 | 0.8720 | exports/E5_results.csv \| Linear Regression + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| 3.5 E5 formula-recovery R2 | 0.9721 | exports/E5_results.csv \| Random Forest Regressor + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| 3.5 E5 formula-recovery R2 | 0.9948 | exports/E5_results.csv \| GBT Regressor + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| 3.5 E4 base AUC | 0.4999 | exports/E4_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| 3.5 cross-check checks | 103 checks, 103 pass (E1 27, E2 25, E3 14, E4 24, E5 13) | faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv | no |
| 3.5 local vs HDFS | 485 rows, 0 flagged, max 6.76e-05 | faculty_evidence/supervised/local_vs_hdfs_comparison.csv and local_vs_hdfs_flags.csv | no |
| 3.5 defective E2 check | failing value 27102.0; 102 of 103 checks passed in the defective copy | faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck_original_with_defect.csv | no |
| 3.5 all-users E2 check | 437 of 437 users pass; old window would flag 131 | faculty_evidence/supervised/E2_nofuture_allusers_check.csv | no |

### Deck v2 (56 entries)

| Where | Value shown | Source | Also in SUPERVISED_REPORT.md |
|---|---|---|---|
| Slide 4 E3/E4 AUC ranges | 0.5425-0.5486; 0.4965-0.4999 | exports/E3_results.csv, E4_results.csv \| ROC AUC \| headline split | no |
| Slide 8 validation AUC | 0.7549 | exports/E1_results.csv \| Random Forest \| ROC AUC \| validation | no |
| Slide 9 validation F1 (macro) | 0.7134 | exports/E1_results.csv \| Random Forest \| F1 (macro) \| validation | no |
| Slide 9 test F1 (macro) | 0.7193 | exports/E1_results.csv \| Random Forest \| F1 (macro) \| test | no |
| Slide 9 validation Baseline accuracy | 0.6096 | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| validation | no |
| Slide 9 test Baseline accuracy | 0.6144 | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| test | yes |
| Slide 9 Accuracy (verified, unchanged) | 0.7352 | exports/E1_results.csv \| Random Forest \| Accuracy \| test | yes |
| Slide 9 F1 (weighted) (verified, unchanged) | 0.7346 | exports/E1_results.csv \| Random Forest \| F1 (weighted) \| test | yes |
| Slide 9 Precision (achieved) (verified, unchanged) | 0.7801 | exports/E1_results.csv \| Random Forest \| Precision (positive class) \| test | no |
| Slide 9 Recall (achieved) (verified, unchanged) | 0.7923 | exports/E1_results.csv \| Random Forest \| Recall (positive class) \| test | no |
| Slide 9 F1 (achieved) (verified, unchanged) | 0.7862 | exports/E1_results.csv \| Random Forest \| F1 (positive class) \| test | no |
| Slide 9 ROC-AUC (verified, unchanged) | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| Slide 9 confusion (verified) TN | 3,676 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Slide 9 confusion (verified) FP | 2,030 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Slide 9 confusion (verified) FN | 1,888 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Slide 9 confusion (verified) TP | 7,202 | faculty_evidence/supervised/predictions/E1_Random_Forest_test.csv (counts of label/prediction) | no |
| Slide 9 baseline | 0.614 | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| test | yes |
| Slide 10 E1 baseline | 0.614 | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| test | yes |
| Slide 10 E1: Random Forest (test) acc | 0.735 | exports/E1_results.csv \| Random Forest \| Accuracy \| test | yes |
| Slide 10 E1: Random Forest (test) AUC | 0.759 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | no |
| Slide 10 E1: Logistic Regression (test) acc | 0.736 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test | no |
| Slide 10 E1: Logistic Regression (test) AUC | 0.740 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test | yes |
| Slide 10 E1: Gradient-Boosted Trees (test) acc | 0.738 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test | yes |
| Slide 10 E1: Gradient-Boosted Trees (test) AUC | 0.773 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test | yes |
| Slide 10 E1 hold-out acc | 0.723 | exports/E1_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| Slide 10 E1 hold-out AUC | 0.750 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| Slide 10 E2 baseline | 0.589 | exports/E2_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| chronological test | no |
| Slide 10 E2: Random Forest (chronological test) acc | 0.582 | exports/E2_results.csv \| Random Forest \| Accuracy \| chronological test | yes |
| Slide 10 E2: Random Forest (chronological test) AUC | 0.671 | exports/E2_results.csv \| Random Forest \| ROC AUC \| chronological test | no |
| Slide 10 E2: Logistic Regression (chronological test) acc | 0.684 | exports/E2_results.csv \| Logistic Regression \| Accuracy \| chronological test | no |
| Slide 10 E2: Logistic Regression (chronological test) AUC | 0.700 | exports/E2_results.csv \| Logistic Regression \| ROC AUC \| chronological test | yes |
| Slide 10 E2: Gradient-Boosted Trees (chronological test) acc | 0.599 | exports/E2_results.csv \| Gradient-Boosted Trees \| Accuracy \| chronological test | yes |
| Slide 10 E2: Gradient-Boosted Trees (chronological test) AUC | 0.697 | exports/E2_results.csv \| Gradient-Boosted Trees \| ROC AUC \| chronological test | yes |
| Slide 10 baseline ROC-AUC | 0.500 | by definition: a classifier that always predicts one class has ROC AUC 0.5 (as on the original slide) | yes |
| Slide 10 E1 accuracy gap (points) | 12.1 to 12.4 | derived: E1 accuracy minus majority baseline (exports/E1_results.csv) | no |
| Slide 10 text baseline | 0.614 | exports/E1_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| test | yes |
| Slide 10 hold-out acc | 0.723 | exports/E1_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| Slide 10 hold-out AUC | 0.750 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| Slide 10 E2 RF acc | 0.582 | exports/E2_results.csv \| Random Forest \| Accuracy \| chronological test | yes |
| Slide 10 E2 baseline text | 0.589 | exports/E2_results.csv \| Random Forest \| Baseline accuracy (always majority class) \| chronological test | no |
| Slide 10 E2 random-split reference | 0.819-0.830 | exports/E2_results.csv \| ROC AUC \| random split (NOT headline) \| REFERENCE | no |
| Slide 11 tiles | 0.54-0.55; 0.50-0.50; 0.61-0.62 | exports/E3_results.csv, E4_results.csv (ROC AUC; E3 REFERENCE coverage-only runs) | no |
| Slide 11 E3 RF acc | 0.5355 | exports/E3_results.csv \| Random Forest \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| Slide 11 E3 LR acc | 0.5378 | exports/E3_results.csv \| Logistic Regression \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| Slide 11 E3 baseline | 0.5011 | exports/E3_results.csv \| Baseline accuracy (always majority class) \| stratified 5-fold CV (out-of-fold) (identical in all model rows) | yes |
| Slide 11 E4 Random Forest acc | 0.5056 | exports/E4_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| Slide 11 E4 Logistic Regression acc | 0.5040 | exports/E4_results.csv \| Logistic Regression \| Accuracy \| test (user-held-out) | yes |
| Slide 11 E4 Gradient-Boosted Trees acc | 0.5036 | exports/E4_results.csv \| Gradient-Boosted Trees \| Accuracy \| test (user-held-out) | yes |
| Slide 11 E4 baseline | 0.5079 | exports/E4_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| Slide 11 E5 RF MAE | 188.6 | exports/E5_results.csv \| Random Forest Regressor \| MAE (kcal) \| test | yes |
| Slide 11 E5 GBT MAE | 183.3 | exports/E5_results.csv \| GBT Regressor \| MAE (kcal) \| test | no |
| Slide 11 E5 LR MAE (verified, unchanged) | 199.7 | exports/E5_results.csv \| Linear Regression \| MAE (kcal) \| test | yes |
| Slide 11 E5 LR RMSE (verified, unchanged) | 263.6 | exports/E5_results.csv \| Linear Regression \| RMSE (kcal) \| test | yes |
| Slide 11 E5 LR R2 (verified, unchanged) | 0.630 | exports/E5_results.csv \| Linear Regression \| R2 \| test | yes |
| Slide 11 E5 baseline MAE | 334.5 | exports/E5_results.csv \| Baseline: training mean \| MAE (kcal) \| test | yes |
| Slide 11 E5 test user-days | 14,985 | SUPERVISED_REPORT.md section 2 (E5 test 14,985) / faculty_evidence/supervised/predictions/E5_splits.csv | yes |

### ML-part guide (179 entries)

| Where | Value shown | Source | Also in SUPERVISED_REPORT.md |
|---|---|---|---|
| 1 at a glance | 100,122 user-days, 437 users | SUPERVISED_REPORT.md section 1/2 (E1-E5 on the Silver daily dataset: 100,122 user-days; E3: 437 users) | no |
| 1.2 table | E2 splits {'train': '50,014', 'validation': '6,513', 'test': '7,647'} cuts 2024-09-08/2024-11-02 goal rates {'train': '0.7378', 'validation': '0.2246', 'test': '0.4114'} | faculty_evidence/supervised/E2_split_summary.csv | no |
| 1.2 table | E1 accuracy range 0.7352–0.7382 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E1 AUC range 0.7396–0.7735 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E2 accuracy range 0.5823–0.6835 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E2 AUC range 0.6706–0.7004 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E3 accuracy range 0.5355–0.5378 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E3 AUC range 0.5425–0.5486 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E4 accuracy range 0.5036–0.5056 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E4 AUC range 0.4965–0.4999 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E5 MAE range 183.28–199.71 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 table | E5 R2 range 0.6296–0.6658 | exports/E<n>_results.csv (model rows of the headline split) | no |
| 1.2 E1 baseline | 0.6144 | exports/E1_results.csv \| Baseline accuracy (always majority class) \| test (identical in all model rows) | yes |
| 1.2 E2 baseline | 0.5886 | exports/E2_results.csv \| Baseline accuracy (always majority class) \| chronological test (identical in all model rows) | yes |
| 1.2 E3 baseline | 0.5011 | exports/E3_results.csv \| Baseline accuracy (always majority class) \| stratified 5-fold CV (out-of-fold) (identical in all model rows) | yes |
| 1.2 E4 baseline | 0.5079 | exports/E4_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| 1.2 E5 baseline MAE | 334.51 | exports/E5_results.csv \| Baseline: training mean \| MAE (kcal) \| test | yes |
| 1.2 golden rule | 0.8191 | exports/E2_results.csv \| Random Forest \| ROC AUC \| random split (NOT headline) \| REFERENCE | yes |
| 1.2 golden rule | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| 1.2 golden rule | 0.6706 | exports/E2_results.csv \| Random Forest \| ROC AUC \| chronological test | yes |
| 2.2 framing | train 70,383 / validation 14,943 / test 14,796 | SUPERVISED_REPORT.md section 2 (E1 splits) / faculty_evidence/supervised/predictions/E1_splits.csv | yes |
| 2.2 framing | E5 train 70,085 / validation 15,052 / test 14,985 | SUPERVISED_REPORT.md section 2 / faculty_evidence/supervised/predictions/E5_splits.csv | no |
| 2.2 framing | E4 users 312/72/53; E3 437 users, 218 high achievers; feature counts 18/20/9/16/10 | SUPERVISED_REPORT.md section 2 / faculty_evidence/supervised/final_feature_set_E1_E5.csv | no |
| 2.2 framing | leak E1: 0.9996–1.0000 vs 0.7396–0.7735 | exports/E1_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| 2.2 framing | leak E2: 0.7518–0.8787 vs 0.6706–0.7004 | exports/E2_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| 2.2 framing | leak E3: 0.7978–0.8242 vs 0.5425–0.5486 | exports/E3_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| 2.2 framing | leak E4: 0.8905–0.9976 vs 0.4965–0.4999 | exports/E4_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| 2.2 framing | leak E5: 0.7032–0.7450 vs 0.6296–0.6658 | exports/E5_results.csv (rows with status INVALID, and the matching VALID row of each base model) | no |
| 2.2 framing | 0.5408 | exports/E3_results.csv \| Random Forest: raw average weight_kg instead of baseline weight (ablation) \| ROC AUC \| stratified 5-fold CV (out-of-fold) \| REFERENCE | no |
| 2.2 framing | 0.5721 | exports/E3_results.csv \| Logistic Regression: raw average weight_kg instead of baseline weight (ablation) \| ROC AUC \| stratified 5-fold CV (out-of-fold) \| REFERENCE | no |
| 2.2 framing | 0.8720 | exports/E5_results.csv \| Linear Regression + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| 2.2 framing | 0.9721 | exports/E5_results.csv \| Random Forest Regressor + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| 2.2 framing | 0.9948 | exports/E5_results.csv \| GBT Regressor + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| 2.4 E1 | 1.6e-06 | faculty_evidence/supervised/E1_reproduction_check.csv (max abs_diff, 14 rows) | no |
| 2.4 E1 | 0.7352 | exports/E1_results.csv \| Random Forest \| Accuracy \| test | yes |
| 2.4 E1 | 0.7346 | exports/E1_results.csv \| Random Forest \| F1 (weighted) \| test | yes |
| 2.4 E1 | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| 2.4 E1 | 0.7232 | exports/E1_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| 2.4 E1 | 0.7498 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| 2.4 E1 | 0.7356 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test | yes |
| 2.4 E1 | 0.7305 | exports/E1_results.csv \| Logistic Regression \| F1 (weighted) \| test | yes |
| 2.4 E1 | 0.7396 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test | yes |
| 2.4 E1 | 0.7315 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test (user-held-out) | yes |
| 2.4 E1 | 0.7340 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test (user-held-out) | yes |
| 2.4 E1 | 0.7382 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test | yes |
| 2.4 E1 | 0.7381 | exports/E1_results.csv \| Gradient-Boosted Trees \| F1 (weighted) \| test | yes |
| 2.4 E1 | 0.7735 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test | yes |
| 2.4 E1 | 0.7224 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test (user-held-out) | yes |
| 2.4 E1 | 0.7608 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
|  | 0.6144 | exports/E1_results.csv \| Baseline accuracy (always majority class) \| test (identical in all model rows) | yes |
|  | 0.6168 | exports/E1_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| 2.4 E1 | 12.1-12.4 percentage points | derived: E1 accuracy minus the majority baseline (exports/E1_results.csv) | yes |
| 2.4 E2 | 0.5823 | exports/E2_results.csv \| Random Forest \| Accuracy \| chronological test | yes |
| 2.4 E2 | 0.4954 | exports/E2_results.csv \| Random Forest \| Precision (positive class) \| chronological test | yes |
| 2.4 E2 | 0.8179 | exports/E2_results.csv \| Random Forest \| Recall (positive class) \| chronological test | yes |
| 2.4 E2 | 0.6170 | exports/E2_results.csv \| Random Forest \| F1 (positive class) \| chronological test | yes |
| 2.4 E2 | 0.6706 | exports/E2_results.csv \| Random Forest \| ROC AUC \| chronological test | yes |
| 2.4 E2 | 0.6835 | exports/E2_results.csv \| Logistic Regression \| Accuracy \| chronological test | yes |
| 2.4 E2 | 0.6649 | exports/E2_results.csv \| Logistic Regression \| Precision (positive class) \| chronological test | yes |
| 2.4 E2 | 0.4654 | exports/E2_results.csv \| Logistic Regression \| Recall (positive class) \| chronological test | yes |
| 2.4 E2 | 0.5475 | exports/E2_results.csv \| Logistic Regression \| F1 (positive class) \| chronological test | yes |
| 2.4 E2 | 0.7004 | exports/E2_results.csv \| Logistic Regression \| ROC AUC \| chronological test | yes |
| 2.4 E2 | 0.5991 | exports/E2_results.csv \| Gradient-Boosted Trees \| Accuracy \| chronological test | yes |
| 2.4 E2 | 0.5080 | exports/E2_results.csv \| Gradient-Boosted Trees \| Precision (positive class) \| chronological test | yes |
| 2.4 E2 | 0.8039 | exports/E2_results.csv \| Gradient-Boosted Trees \| Recall (positive class) \| chronological test | yes |
| 2.4 E2 | 0.6226 | exports/E2_results.csv \| Gradient-Boosted Trees \| F1 (positive class) \| chronological test | yes |
| 2.4 E2 | 0.6970 | exports/E2_results.csv \| Gradient-Boosted Trees \| ROC AUC \| chronological test | yes |
| 2.4 E2 | 0.4114 | exports/E2_results.csv \| Random Forest \| Baseline accuracy (always TRAINING-majority class) \| chronological test | yes |
| 2.4 E2 | 0.7732 | exports/E2_results.csv \| Random Forest \| Accuracy \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E2 | 0.8191 | exports/E2_results.csv \| Random Forest \| ROC AUC \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E2 | 0.7770 | exports/E2_results.csv \| Logistic Regression \| Accuracy \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E2 | 0.8295 | exports/E2_results.csv \| Logistic Regression \| ROC AUC \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E2 | 0.7780 | exports/E2_results.csv \| Gradient-Boosted Trees \| Accuracy \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E2 | 0.8301 | exports/E2_results.csv \| Gradient-Boosted Trees \| ROC AUC \| random split (NOT headline) \| REFERENCE | yes |
| 2.4 E3 | 0.5355 | exports/E3_results.csv \| Random Forest \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.5318 | exports/E3_results.csv \| Random Forest \| F1 (weighted) \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.5425 | exports/E3_results.csv \| Random Forest \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.5446 | exports/E3_results.csv \| Random Forest \| ROC AUC (mean over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.0377 | exports/E3_results.csv \| Random Forest \| ROC AUC (sd over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.5378 | exports/E3_results.csv \| Logistic Regression \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.5361 | exports/E3_results.csv \| Logistic Regression \| F1 (weighted) \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.5486 | exports/E3_results.csv \| Logistic Regression \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.5725 | exports/E3_results.csv \| Logistic Regression \| ROC AUC (mean over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.0332 | exports/E3_results.csv \| Logistic Regression \| ROC AUC (sd over folds) \| stratified 5-fold CV (out-of-fold) | yes |
| 2.4 E3 | 0.6077 | exports/E3_results.csv \| Random Forest: logging-window coverage ONLY (mean logged month) \| ROC AUC \| stratified 5-fold CV (out-of-fold) \| REFERENCE | yes |
| 2.4 E3 | 0.6195 | exports/E3_results.csv \| Logistic Regression: logging-window coverage ONLY (mean logged month) \| ROC AUC \| stratified 5-fold CV (out-of-fold) \| REFERENCE | yes |
| 2.4 E3 | standard error about 2.4 percentage points | SUPERVISED_REPORT.md section 3.3 (derived: sqrt(p(1-p)/n)) | no |
| 2.4 E4 | 0.5056 | exports/E4_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| 2.4 E4 | 0.4406 | exports/E4_results.csv \| Random Forest \| F1 (macro) \| test (user-held-out) | yes |
| 2.4 E4 | 0.4965 | exports/E4_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| 2.4 E4 | 0.5040 | exports/E4_results.csv \| Logistic Regression \| Accuracy \| test (user-held-out) | yes |
| 2.4 E4 | 0.4442 | exports/E4_results.csv \| Logistic Regression \| F1 (macro) \| test (user-held-out) | yes |
| 2.4 E4 | 0.4999 | exports/E4_results.csv \| Logistic Regression \| ROC AUC \| test (user-held-out) | yes |
| 2.4 E4 | 0.5036 | exports/E4_results.csv \| Gradient-Boosted Trees \| Accuracy \| test (user-held-out) | yes |
| 2.4 E4 | 0.5002 | exports/E4_results.csv \| Gradient-Boosted Trees \| F1 (macro) \| test (user-held-out) | yes |
| 2.4 E4 | 0.4999 | exports/E4_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| 2.4 E5 | 199.71 | exports/E5_results.csv \| Linear Regression \| MAE (kcal) \| test | yes |
| 2.4 E5 | 263.64 | exports/E5_results.csv \| Linear Regression \| RMSE (kcal) \| test | yes |
| 2.4 E5 | 0.6296 | exports/E5_results.csv \| Linear Regression \| R2 \| test | yes |
| 2.4 E5 | 247.20 | exports/E5_results.csv \| Linear Regression \| MAE (kcal) \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | 0.5804 | exports/E5_results.csv \| Linear Regression \| R2 \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | 188.61 | exports/E5_results.csv \| Random Forest Regressor \| MAE (kcal) \| test | yes |
| 2.4 E5 | 258.68 | exports/E5_results.csv \| Random Forest Regressor \| RMSE (kcal) \| test | yes |
| 2.4 E5 | 0.6434 | exports/E5_results.csv \| Random Forest Regressor \| R2 \| test | yes |
| 2.4 E5 | 238.85 | exports/E5_results.csv \| Random Forest Regressor \| MAE (kcal) \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | 0.5909 | exports/E5_results.csv \| Random Forest Regressor \| R2 \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | 183.28 | exports/E5_results.csv \| GBT Regressor \| MAE (kcal) \| test | yes |
| 2.4 E5 | 250.41 | exports/E5_results.csv \| GBT Regressor \| RMSE (kcal) \| test | yes |
| 2.4 E5 | 0.6658 | exports/E5_results.csv \| GBT Regressor \| R2 \| test | yes |
| 2.4 E5 | 235.86 | exports/E5_results.csv \| GBT Regressor \| MAE (kcal) \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | 0.6087 | exports/E5_results.csv \| GBT Regressor \| R2 \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | 247.40 | exports/E5_results.csv \| Baseline: Linear Regression on active_minutes only \| MAE (kcal) \| test | yes |
| 2.4 E5 | 337.99 | exports/E5_results.csv \| Baseline: Linear Regression on active_minutes only \| RMSE (kcal) \| test | yes |
| 2.4 E5 | 0.3912 | exports/E5_results.csv \| Baseline: Linear Regression on active_minutes only \| R2 \| test | yes |
| 2.4 E5 | 433.17 | exports/E5_results.csv \| Baseline: training mean \| RMSE (kcal) \| test | yes |
| 2.4 E5 | -0.0000 | exports/E5_results.csv \| Baseline: training mean \| R2 \| test | yes |
| 2.4 E5 | 395.21 | exports/E5_results.csv \| Baseline: training mean \| MAE (kcal) \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | -0.1630 | exports/E5_results.csv \| Baseline: training mean \| R2 \| chronological test (>= 2024-10-15) | yes |
| 2.4 E5 | 0.0 | faculty_evidence/supervised/E5_reproduction_check.csv (max abs_diff, 3 rows) | yes |
| 2.6 verification | 17 leakage runs, all INVALID | exports/E1..E5_results.csv (status INVALID, metric ROC AUC / R2) and the matching VALID base-model row | no |
| 2.6 verification | 103 checks, 103 pass; by experiment {'E1': (27, 27), 'E2': (25, 25), 'E3': (14, 14), 'E4': (24, 24), 'E5': (13, 13)}; largest difference 0.0235 | faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv | no |
| 2.6 defective E2 check | user 2094, cut day 2024-06-05 | faculty_evidence/supervised/E2_nofuture_allusers_check.csv (row with the largest old-window change among the 25 sampled users) | yes |
| 2.6 defective E2 check | 5.0e-07 (tolerance 2e-05) | SUPERVISED_REPORT.md section 4.3 / faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv (features checks) | no |
| 2.6 defective E2 check | 21:33:53 / 23:11:02 / 23:11:41 on 18 Oct | SUPERVISED_REPORT.md section 4.3 (file modification times; not from a CSV) | no |
| 2.6 local vs hdfs | 485 rows, 0 flagged, max 6.7596e-05; 325 of 348 metric rows exactly equal | faculty_evidence/supervised/local_vs_hdfs_comparison.csv and local_vs_hdfs_flags.csv | no |
| 2.6 local vs hdfs | 9.36e-06 | faculty_evidence/supervised/local_vs_hdfs_comparison.csv (metric rows, status VALID/BASELINE/REFERENCE) | yes |
| 2.8 unknowns | 15 local E1 checks (12 test, 0 validation, 3 baseline); 27 HDFS E1 checks, 12 validation; 16:19:47, 16:23:17, 16:23:33; 3 min 46 s | SUPERVISED_REPORT.md section 5.1 (file listings and modification times; not from a CSV) | no |
| 2.8 unknowns | 60 valid and baseline E1 rows within 9.36e-06 | faculty_evidence/supervised/local_vs_hdfs_comparison.csv (E1 rows, VALID/BASELINE) | no |
| 2.8 unknowns | 5.68e-14 | faculty_evidence/supervised/local_vs_hdfs_comparison.csv (E5 metric rows) | yes |
| 2.8 unknowns | 17:16:43, 17:16:44/45, 17:22:29, 17:22:34, 19:27:07-19:27:09, 2 h 4 min 38 s, 21:20:59, 21:33:21, 12 min 22 s | SUPERVISED_REPORT.md section 5.3 (file modification times; not from a CSV) | no |
| 3 limitations | 0.4999 | exports/E4_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| 4 viva | 0.7232 | exports/E1_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| 4 viva | 0.7498 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| 4 viva | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| 4 viva | 0.9895 | exports/E1_results.csv \| Random Forest + steps & distance_km (LEAKAGE) \| Accuracy \| test \| INVALID | no |
| 4 viva | 0.9996 | exports/E1_results.csv \| Random Forest + steps & distance_km (LEAKAGE) \| ROC AUC \| test \| INVALID | yes |
| 4 viva | 395.21 | exports/E5_results.csv \| Baseline: training mean \| MAE (kcal) \| chronological test (>= 2024-10-15) | yes |
| Appendix B | 0.7352 | exports/E1_results.csv \| Random Forest \| Accuracy \| test | yes |
| Appendix B | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| Appendix B | 0.7356 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test | yes |
| Appendix B | 0.7396 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test | yes |
| Appendix B | 0.7382 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test | yes |
| Appendix B | 0.7735 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test | yes |
| Appendix B | 0.7232 | exports/E1_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| Appendix B | 0.7498 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
| Appendix B | 0.7315 | exports/E1_results.csv \| Logistic Regression \| Accuracy \| test (user-held-out) | yes |
| Appendix B | 0.7340 | exports/E1_results.csv \| Logistic Regression \| ROC AUC \| test (user-held-out) | yes |
| Appendix B | 0.7224 | exports/E1_results.csv \| Gradient-Boosted Trees \| Accuracy \| test (user-held-out) | yes |
| Appendix B | 0.7608 | exports/E1_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| Appendix B | 0.5823 | exports/E2_results.csv \| Random Forest \| Accuracy \| chronological test | yes |
| Appendix B | 0.6706 | exports/E2_results.csv \| Random Forest \| ROC AUC \| chronological test | yes |
|  | 0.5886 | exports/E2_results.csv \| Baseline accuracy (always majority class) \| chronological test (identical in all model rows) | yes |
| Appendix B | 0.6835 | exports/E2_results.csv \| Logistic Regression \| Accuracy \| chronological test | yes |
| Appendix B | 0.7004 | exports/E2_results.csv \| Logistic Regression \| ROC AUC \| chronological test | yes |
| Appendix B | 0.5991 | exports/E2_results.csv \| Gradient-Boosted Trees \| Accuracy \| chronological test | yes |
| Appendix B | 0.6970 | exports/E2_results.csv \| Gradient-Boosted Trees \| ROC AUC \| chronological test | yes |
| Appendix B | 0.5355 | exports/E3_results.csv \| Random Forest \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| Appendix B | 0.5425 | exports/E3_results.csv \| Random Forest \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
|  | 0.5011 | exports/E3_results.csv \| Baseline accuracy (always majority class) \| stratified 5-fold CV (out-of-fold) (identical in all model rows) | yes |
| Appendix B | 0.5378 | exports/E3_results.csv \| Logistic Regression \| Accuracy \| stratified 5-fold CV (out-of-fold) | yes |
| Appendix B | 0.5486 | exports/E3_results.csv \| Logistic Regression \| ROC AUC \| stratified 5-fold CV (out-of-fold) | yes |
| Appendix B | 0.5056 | exports/E4_results.csv \| Random Forest \| Accuracy \| test (user-held-out) | yes |
| Appendix B | 0.4965 | exports/E4_results.csv \| Random Forest \| ROC AUC \| test (user-held-out) | yes |
|  | 0.5079 | exports/E4_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| Appendix B | 0.5040 | exports/E4_results.csv \| Logistic Regression \| Accuracy \| test (user-held-out) | yes |
| Appendix B | 0.4999 | exports/E4_results.csv \| Logistic Regression \| ROC AUC \| test (user-held-out) | yes |
| Appendix B | 0.5036 | exports/E4_results.csv \| Gradient-Boosted Trees \| Accuracy \| test (user-held-out) | yes |
| Appendix B | 0.4999 | exports/E4_results.csv \| Gradient-Boosted Trees \| ROC AUC \| test (user-held-out) | yes |
| Appendix B | 199.71 | exports/E5_results.csv \| Linear Regression \| MAE (kcal) \| test | yes |
| Appendix B | 263.64 | exports/E5_results.csv \| Linear Regression \| RMSE (kcal) \| test | yes |
| Appendix B | 0.6296 | exports/E5_results.csv \| Linear Regression \| R2 \| test | yes |
| Appendix B | 188.61 | exports/E5_results.csv \| Random Forest Regressor \| MAE (kcal) \| test | yes |
| Appendix B | 258.68 | exports/E5_results.csv \| Random Forest Regressor \| RMSE (kcal) \| test | yes |
| Appendix B | 0.6434 | exports/E5_results.csv \| Random Forest Regressor \| R2 \| test | yes |
| Appendix B | 183.28 | exports/E5_results.csv \| GBT Regressor \| MAE (kcal) \| test | yes |
| Appendix B | 250.41 | exports/E5_results.csv \| GBT Regressor \| RMSE (kcal) \| test | yes |
| Appendix B | 0.6658 | exports/E5_results.csv \| GBT Regressor \| R2 \| test | yes |
| Appendix B | 433.17 | exports/E5_results.csv \| Baseline: training mean \| RMSE (kcal) \| test | yes |
| Appendix B | -0.0000 | exports/E5_results.csv \| Baseline: training mean \| R2 \| test | yes |

### Member-contributions review (28 entries)

| Where | Value shown | Source | Also in SUPERVISED_REPORT.md |
|---|---|---|---|
| member | 0.6144 | exports/E1_results.csv \| Baseline accuracy (always majority class) \| test (identical in all model rows) | yes |
| member | 0.5886 | exports/E2_results.csv \| Baseline accuracy (always majority class) \| chronological test (identical in all model rows) | yes |
| member | 0.5011 | exports/E3_results.csv \| Baseline accuracy (always majority class) \| stratified 5-fold CV (out-of-fold) (identical in all model rows) | yes |
| member | 0.5079 | exports/E4_results.csv \| Baseline accuracy (always majority class) \| test (user-held-out) (identical in all model rows) | yes |
| member E5 baseline | 334.51 | exports/E5_results.csv \| Baseline: training mean \| MAE (kcal) \| test | yes |
| member review | E2 split {'train': '50,014', 'validation': '6,513', 'test': '7,647'}, goal rates {'train': '0.7378', 'validation': '0.2246', 'test': '0.4114'}, cuts 2024-09-08/2024-11-02 | faculty_evidence/supervised/E2_split_summary.csv | no |
| member review | 17 leakage runs | exports/E1..E5_results.csv (status INVALID) | yes |
| member review | leak E1: 0.9996–1.0000 vs 0.7396–0.7735 | exports/E1_results.csv (INVALID rows and the matching VALID base-model rows) | no |
| member review | leak E2: 0.7518–0.8787 vs 0.6706–0.7004 | exports/E2_results.csv (INVALID rows and the matching VALID base-model rows) | no |
| member review | leak E3: 0.7978–0.8242 vs 0.5425–0.5486 | exports/E3_results.csv (INVALID rows and the matching VALID base-model rows) | no |
| member review | leak E4: 0.8905–0.9976 vs 0.4965–0.4999 | exports/E4_results.csv (INVALID rows and the matching VALID base-model rows) | no |
| member review | leak E5: 0.7032–0.7450 vs 0.6296–0.6658 | exports/E5_results.csv (INVALID rows and the matching VALID base-model rows) | no |
| member review | cross-check 103/103 {'E1': (27, 27), 'E2': (25, 25), 'E3': (14, 14), 'E4': (24, 24), 'E5': (13, 13)}, largest 0.0235; compare 485 rows 0 flagged max 6.7596e-05, valid 9.36e-06, exact 325/348 | faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv; local_vs_hdfs_comparison.csv; local_vs_hdfs_flags.csv | no |
| member review | defective 27102.0; all-users {'users': 437, 'passed': 437, 'flagged_old': 131, 'max_corrected': 0.0, 'max_old': 29274.0, 'sample_users': 25, 'sample_flagged': 5, 'sample_max_old': 27102.0} | faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck_original_with_defect.csv; E2_nofuture_allusers_check.csv | no |
| member review | 0.8720 | exports/E5_results.csv \| Linear Regression + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| member review | 0.9721 | exports/E5_results.csv \| Random Forest Regressor + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| member review | 0.9948 | exports/E5_results.csv \| GBT Regressor + activity_type & intensity (formula recovery) \| R2 \| test \| REFERENCE | yes |
| Abhirami section | E1 ranges 0.7352–0.7382 0.7396–0.7735 0.7224–0.7315 0.7340–0.7608 | exports/E<n>_results.csv (model rows of the headline split) | no |
| Abhirami section | E2 ranges 0.5823–0.6835 0.6706–0.7004 0.8191–0.8301 | exports/E<n>_results.csv (model rows of the headline split) | no |
| Abhirami section | E3 ranges 0.5355–0.5378 0.5425–0.5486 [0.0377378860999523, 0.0332051974773902] | exports/E<n>_results.csv (model rows of the headline split) | no |
| Abhirami section | E4 ranges 0.5036–0.5056 0.4965–0.4999 | exports/E<n>_results.csv (model rows of the headline split) | no |
| Abhirami section | E5 ranges 183.28–199.71 0.6296–0.6658 0.5804–0.6087 | exports/E<n>_results.csv (model rows of the headline split) | no |
| Abhirami section | 15 / 27 E1 checks; 16:23:33; 3 min 46 s; 60 rows within 9.36e-06; 17:16:43; 17:22:29; 19:27:07-19:27:09; 2 h 4 min 38 s; 12 min 22 s | SUPERVISED_REPORT.md sections 5.1 and 5.3 (file modification times and listings; not from a CSV) | no |
| other sections | 0.7352 | exports/E1_results.csv \| Random Forest \| Accuracy \| test | yes |
| other sections | 0.7585 | exports/E1_results.csv \| Random Forest \| ROC AUC \| test | yes |
| other sections | 199.71 | exports/E5_results.csv \| Linear Regression \| MAE (kcal) \| test | yes |
| other sections | 0.6296 | exports/E5_results.csv \| Linear Regression \| R2 \| test | yes |
| other sections | 199.71 / 263.64 / 0.6296 / 334.51 | exports/E5_results.csv \| Linear Regression and Baseline: training mean \| test | no |

## 5b. Numbers added or re-checked in the second pass

The computations below are read-only. They were run with the project `.venv` Python from the scratch folder (`work/second_pass_numbers.py`; results in `work/second_pass_numbers.json`); nothing was written into the project.

### Random Forest grid (Report 2.2, deck slide 8 and its notes)

| Setting | Validation ROC AUC | Source |
|---|---|---|
| 50 trees, maxDepth 5 | 0.7269 | `faculty_evidence/report_aligned/rf_tuning_grid.csv` (status ok), rounded to 4 decimals |
| 50 trees, maxDepth 10 | 0.7492 | `faculty_evidence/report_aligned/rf_tuning_grid.csv` (status ok), rounded to 4 decimals |
| 50 trees, maxDepth 15 | 0.7549 | `faculty_evidence/report_aligned/rf_tuning_grid.csv` (status ok), rounded to 4 decimals |
| 50 trees, maxDepth 20 | 0.7541 | `faculty_evidence/report_aligned/rf_tuning_grid.csv` (status ok), rounded to 4 decimals |
| 100 trees, maxDepth 5 | 0.7294 | `faculty_evidence/report_aligned/rf_tuning_grid.csv` (status ok), rounded to 4 decimals |
| 100 trees, maxDepth 10 | 0.7544 | `faculty_evidence/report_aligned/rf_tuning_grid.csv` (status ok), rounded to 4 decimals |
| 100 trees, maxDepth 15 | not run | `faculty_evidence/report_aligned/rf_tuning_grid.csv` status 'NOT RUN: OutOfMemoryError (JVM heap)'; `faculty_evidence/log_report_rf_hdfs_attempt1_full_grid.txt` (java.lang.OutOfMemoryError, stage 636); `faculty_evidence/log_report_rf_hdfs.txt` lines 21-22 |
| 100 trees, maxDepth 20 | not run | `faculty_evidence/report_aligned/rf_tuning_grid.csv` status 'NOT RUN: OutOfMemoryError (JVM heap)'; `faculty_evidence/log_report_rf_hdfs_attempt1_full_grid.txt` (java.lang.OutOfMemoryError, stage 636); `faculty_evidence/log_report_rf_hdfs.txt` lines 21-22 |
| Final model, validation ROC AUC | 0.7549 | `exports/E1_results.csv` (Random Forest, ROC AUC, validation = 0.754869); equals the grid value at 50 trees, depth 15 (0.754868) |

Statement 'an earlier search that E1 reuses': `models/sup_e1_goal_same_day.py` (header lines 5-6) takes the Random Forest setting from `faculty_evidence/report_aligned/rf_run_info.json`; `faculty_evidence/supervised/E1_tuning_grid.csv` holds only the Logistic Regression and Gradient-Boosted Trees grids, and `E1_run_info.json` records numTrees 50 and maxDepth 15 (`same_split_as_existing_E1`: true). The grid files are dated 11 Oct 2026 (before the supervised runs).

### Weight and steps (Report 2.5): exact query on the Silver Parquet

```python
import glob, pandas as pd
P = r"D:\bigdata\fitpulsee\FitPulse"
s = pd.concat([pd.read_parquet(f, columns=["user_id", "date", "steps", "weight_kg"])
               for f in sorted(glob.glob(P + r"\data\processed\fitpulse_silver\month=*\*.parquet"))], ignore_index=True)   # 96 files, read-only
s["date"] = pd.to_datetime(s["date"])
rng = s.groupby("user_id").weight_kg.agg(lambda x: x.max() - x.min())      # lightest to heaviest day, per user
rng.median(), rng.mean(), rng.min(), rng.max()
m = s.groupby(s.date.dt.month).weight_kg.mean()                            # monthly mean weight
h1 = s[s.date.dt.month <= 6].steps; h2 = s[s.date.dt.month >= 7].steps
h1.mean(), h1.size, h2.mean(), h2.size
```

| Value in the document | Computed value |
|---|---|
| 'about 59 kg between a user's lightest and heaviest day' | per-user range: median 58.80 kg, mean 58.79 kg, minimum 53.10 kg, maximum 67.00 kg (437 users) |
| 'a median of 58.8 kg over the 437 users' | median of the per-user range = 58.80 kg |
| 'rises steadily through the year' (unchanged wording) | monthly mean weight rises in every month: January 67.85 kg to December 122.26 kg (rises_every_month = True) |
| 'about 9,600 in the first half of the year' and '9,574' | mean steps per user-day, January to June = 9,574.2 (56,937 user-days) |
| 'about 7,400 in the second' and '7,373' | mean steps per user-day, July to December = 7,373.0 (43,185 user-days); the data ends on 2024-12-25 |

### Appendix A of the guide: every number re-checked

| Statement in Appendix A | Check | Result |
|---|---|---|
| Kaggle fitness dataset, 687,701 rows, 3,000 participants | computed: `pd.read_csv(<kagglehub cache>/jijagallery/fitlife-health-and-fitness-tracking-dataset/versions/1/health_fitness_dataset.csv)`; `len(src)` and `src.participant_id.nunique()`; also `faculty_evidence/provenance_check.md` (first rows) | 687,701 and 3,000 |
| 437 participants sampled with seed 42, full years kept | computed: `set(pd.Series(src.participant_id.unique()).sample(n=437, random_state=42)) == set(data/raw/fitpulse_raw.csv user_id)`; Kaggle rows of those 437 users | True; 100,122 rows, equal to the Bronze file |
| Bronze is the raw CSV (100,122 rows, 23 columns) | computed: `pd.read_csv('data/raw/fitpulse_raw.csv').shape`; 437 distinct users | (100122, 23) |
| Silver: partitioned Parquet (39 columns); your models read Silver | computed: `pd.read_parquet('data/processed/fitpulse_silver').shape`; the 39 columns include the month partition column (each file has 38); also `faculty_evidence/hdfs/etl_hdfs_run_report.json` (silver_columns 39) | (100122, 39); 437 users; 0 duplicate (user_id, date) rows |
| 12 partitions, 96 files | computed: `glob('.../fitpulse_silver/month=*/*.parquet')`; also `faculty_evidence/hdfs/verification_summary.json` ('12 partitions, 96 parquet files') | 96 files in 12 month folders |
| 16 of 16 verification checks pass; fsck reports Silver healthy | read: `faculty_evidence/hdfs/verification_summary.json` (passed 16, total 16); `faculty_evidence/hdfs/06_fsck_silver.txt` ('The filesystem under path /fitpulse/silver is HEALTHY'). Not re-run. | 16 of 16; HEALTHY |
| Hadoop 3.4.1, one NameNode and one DataNode, replication 1, hdfs://localhost:9000 | read: `README.md` lines 115 and 133; `faculty_evidence/spark_hdfs_evidence.txt` line 10 (client library 3.4.1); `tools/hadoop-3.4.1` exists; `faculty_evidence/hdfs/06_fsck_silver.txt` (replication=1); `verification_summary.json` (hdfs_uri). Not re-run. | as stated |
| The Spark ETL dropped 0 rows | read: `faculty_evidence/hdfs/etl_hdfs_run_report.json` (bronze_rows 100122, clean_rows 100122, silver_rows_written 100122) | 0 rows dropped |
| HDFS Silver equals local Silver: 0 rows in each direction | read: `faculty_evidence/hdfs/08_spark_hdfs_checks.txt` line 55 ('local-minus-hdfs=0, hdfs-minus-local=0') | 0 and 0 |
| 'Seven steps' in the ETL answer | Not a measured number: the guide's own enumeration in the same sentence (read Bronze; clean; weekday, month and rest-day flag; lag and rolling features; personal goal by group-by and broadcast join; goal_achieved labels; write Parquet partitioned by month). `etl/spark_etl.py` has these stages as comments (lines 106 to 180) but does not number them. | 7 items in the sentence; consistent with the script, not independently counted |
| References 'notebook section 4.1' and 'notebook section 11.5' | computed: `FitPulse_Faculty_Demo.ipynb` cell 33 '### 4.1 Data Cleaning' and cell 83 '# 11.5 HDFS Silver vs local-Parquet Silver' | both exist in the rebuilt notebook |

### Deleted

ROC-AUC 0.755 (legacy web-page Logistic Regression): removed from deck slide 14 and from the member review in three places; not replaced, as instructed. The read-only recomputation done for the review (ROC-AUC 0.7546, accuracy 0.8698, F1 0.2236 on 9,760 rows from 2024-10-15 to 2024-12-24, `models/artifacts/goal_achievement_model.joblib`) is not used in any document.

## 6. Numbers in text I did not rewrite (not re-sourced)

### Report v3

- The project uses the wearable fitness dataset fitpulse_raw.csv, which exceeds the target of 100,000 records so that distributed processing is meaningful. It contains 100,122 daily records from 437 users (about 229 days per user, 1 January to 25 December 2024) described by 23 attributes, listed in Table 1. Each record is one user-day. The number of records actually loaded is 100,122. ... (numbers: 1, 100,000, 100,122, 2024, 229, 23, 25, 437)
- Each record is one user-day, and there are no duplicate user-date pairs. In every record active_minutes + sedentary_minutes + sleep_minutes equals 1,440 (the minutes in a day), so these three variables are not independent. The health_condition column is blank for 69.7% of records and is not used in either model. Units follow the dataset as supplied. ... (numbers: 1,440, 69.7%)
- Given a feature vector describing a user's recorded activity, the model predicts a class label: 1 if the user achieves the fitness goal and 0 otherwise. The goal used to create the label is a daily step target: GoalAchieved = 1 if steps ≥ 8,000 on that day, otherwise 0. 61.3% of the 100,122 records meet this goal. The inputs are the wearable-data features listed in Table 5, which do not include steps or any variable that is almost a copy of steps. ... (numbers: 0, 1, 100,122, 5, 61.3%, 8,000)
- Any variable used to define the goal label must be excluded from the input features; otherwise the model would see the answer (target leakage) and its accuracy would be misleadingly high. Here the label is defined from steps, so steps is excluded, and so is distance_km, which is almost a rescaling of steps (correlation 0.94). As a check, a Random Forest trained with steps and distance_km included reached 98.95% accuracy on a held-out split, confirming that such inputs hand the model the answer. For the same reason the steps-per-active-minute feature proposed in the original design is not used, because it contains steps. ... (numbers: 0.94, 98.95%)
- With 100,000 or more records, training and evaluating the model on a single machine becomes slow. Spark MLlib distributes the data across the cluster so the same classification workflow scales as the dataset grows. ... (numbers: 100,000)
- Random Forest is an ensemble of decision trees. Each tree is trained on a bootstrap sample of the training data and, at every split, considers only a random subset of the features. For a new user, every tree votes and the majority class is the prediction (Figure 2). The Spark MLlib implementation RandomForestClassifier is used. ... (numbers: 2)
- Table 6 explains why Random Forest suits wearable data. Compared with a single decision tree it is far less prone to overfitting, and compared with logistic regression it captures nonlinear relationships and feature interactions without manual transformation. ... (numbers: 6)

Unchanged table cells with numbers: Table 1 (dataset features: 437 distinct users, the date range, ranges such as 20 to 120 active minutes, 16 to 100 sleep score, 69.7% blank health_condition, 1 to 10 stress, 1.5 to 3.5 hydration), Table 2 (HDFS replication factor 3 on a cluster, 1 here), Table 5 (steps >= 8,000), Tables 9 and 10 (verified against the CSVs, exact match: confusion matrix and the five top importances). Of the sentence-level numbers above, 98.95% was verified against `E1_results.csv` (accuracy of the leakage run); 61.3%, 0.94, 69.7%, 229 days per user, 23 attributes and 1,440 minutes are dataset facts that are not in the allowed sources.

### Deck v2 (paragraphs identical in both decks and containing digits)

- **Slide 1**
  - RA2411028010080  —  Abhirami
  - RA2411028010129  —  Prajin Sivakumar
  - RA2411028010086  —  Mahendran palani
  - Good morning. This is Review 2 for FitPulse – Personalized Fitness and Activity Analytics using Big Data. Team: Abhirami, Prajin Sivakumar a
- **Slide 2**
  - FitPulse · Review 2 · SRMIST
  - We follow the Review 2 outline: dataset, proposed model, architecture, preprocessing and its results, classification and its results, compar
- **Slide 3**
  - FitPulse · Review 2 · SRMIST
  - 1 Jan – 25 Dec 2024
  - ~229 days per user
  - Exercise-level minutes (20–120)
  - heart rate (3 fields)
  - Source: public Kaggle fitness dataset. Some columns (calories, distance, active/sedentary/sleep minutes, max heart rate, sleep quality) are 
  - 687,701 raw rows → 100,122 user-day rows; 0 rows removed in cleaning
  - Active + sedentary + sleep = 1,440 min every day
  - Silver adds lag and rolling features (39 columns)
  - Classifier label: steps ≥ 8,000 (61.3% of days)
  - The data is a public Kaggle fitness dataset, with some columns derived by our Spark script, stored as data/raw/fitpulse_raw.csv: 687,701 raw
- **Slide 4**
  - 2. Proposed Model
  - FitPulse · Review 2 · SRMIST
  - Proposed classifier · same-day goal ≥ 8,000 steps
  - Leakage control: steps and distance excluded (control run with them: 98.95%)
- **Slide 5**
  - 3. Overall System Architecture
  - FitPulse · Review 2 · SRMIST
  - replication 1
  - HDFS 3.4.1, 1 node; Silver = 96 Parquet files
  - Spark 4.0.1 – parallel ETL
  - The pipeline: raw CSV stored in HDFS, cleaned, transformed by Spark ETL and feature engineering into the Silver dataset, stored in HDFS or l
- **Slide 6**
  - 4. Preprocessing and Big Data Steps
  - FitPulse · Review 2 · SRMIST
  - Correlations: steps vs distance r = 0.94; minutes sum to 1,440
  - Spark processes data partitions in parallel in memory; HDFS stores files as replicated blocks (replication 1 on our single node).
- **Slide 7**
  - 5. Results of Preprocessing
  - FitPulse · Review 2 · SRMIST
  - Cleaning checks found no duplicates, negative steps, invalid heart rates or missing numeric values, so nothing was removed. The class balanc
- **Slide 8**
  - 6. Classification
  - FitPulse · Review 2 · SRMIST
  - Target: GoalAchieved = 1 if steps ≥ 8,000
  - 18 features: 15 numeric (activity, heart rate, sleep, active_ratio, age, bmi, height, weight, stress, hydration) + 3 categorical (intensity,
  - Excluded: steps (defines label), distance_km (r = 0.94), user_id, date, smoking_status, health_condition
  - 50 trees, depth 15
- **Slide 9**
  - 7. Results of Classification
  - FitPulse · Review 2 · SRMIST
  - F1 (weighted)
  - F1 (achieved)
  - 12 points above the 0.614 majority baseline
  - Finds 79.2% of achieved days; flags 64.4% of missed days (3,676 of 5,706)
- **Slide 10**
  - 8. Comparison with Majority-Class Baseline
  - FitPulse · Review 2 · SRMIST
  - A run with steps and distance reached 98.95%: target leakage, not a valid classifier
- **Slide 11**
  - FitPulse · Review 2 · SRMIST
  - E5 · Linear Regression: daily calories
- **Slide 12**
  - 10. Plan of Action / Member Tasks
  - FitPulse · Review 2 · SRMIST
  - Power BI, 5 pages (CSV import)
  - Report and Review 2 slides
  - RA2411028010129
  - RA2411028010080
  - Machine learning: five experiments (E1–E5) and how we verified them
  - RA2411028010086
  - Dashboards and insights: Power BI (5 pages) and the per-user web page (localhost)
- **Slide 13**
  - 11. Power BI Dashboard and Insights
  - FitPulse · Review 2 · SRMIST
  - Fitness Overview page (1 of 5 pages)
  - 437 users · 100,122 user-days
  - Average 8,625 steps, 662.2 kcal and 69.9 active minutes per day
  - 33.8% goal achievement
  - Goal = 1.10 × each user's own average steps (not the fixed 8,000 of the classifier)
  - Weekends about 2× weekdays
  - Goal achievement is 56–57% on Saturday and Sunday vs 24–25% on weekdays (recomputed from the Silver data)
  - Steps peak near 10,100 in March and dip in autumn while calories climb through the year
- **Slide 14**
  - 12. Localhost: HDFS and Web Page
  - FitPulse · Review 2 · SRMIST
  - http://localhost:9870
  - /fitpulse/silver/month=2024-03
  - .\run_fitpulse_hdfs.ps1 -SkipEtl
  - Single node, replication factor 1
  - Silver layer: 96 Parquet files, partitioned by month
  - .\webapp\run_local.ps1
- **Slide 15**
  - 13. References
  - FitPulse · Review 2 · SRMIST
  - [1]  L. Breiman, "Random forests," Machine Learning, vol. 45, no. 1, pp. 5–32, 2001.
- **Slide 16**
  - 14. Implementation Link
  - FitPulse · Review 2 · SRMIST
  - PySpark 4.0.1, Hadoop HDFS 3.4.1 (single node), Spark MLlib
  - FitPulse_PowerBI_Dashboard.pbix (5 pages, CSV import); webapp (localhost only)
  - The implementation is in the FitPulse project: the faculty demo notebook and the Spark scripts listed here. It runs locally with PySpark and

### ML-part guide

- Appendix A (upstream stages) is carried over verbatim, with its numbers (for example 687,701 rows, 3,000 participants, 39 columns, 12 partitions and 96 files, 16 of 16 verification checks). **Re-checked in the second pass; every number is listed in 5b.**

### Member-contributions review

- Prajin's section (data, Spark, HDFS) and the unedited parts of Mahendran's section (Power BI cards 8,625 / 662.2 / 69.9 / 33.8%, the Cycling slicer test, the web-page checks, the git table) are unchanged and keep the source files they name in the document.

## 7. Method and tools

- Copies were edited with python-docx and python-pptx (formatted elements cloned from the originals, text set run by run), validated with the docx and pptx skills' `validate.py`, and rendered with Microsoft Word and PowerPoint (private instances, scratch copies) to PDF and then to images with PyMuPDF (installed in a scratch folder outside the project and the `.venv`).
- LibreOffice and Poppler, which the skills assume, are not installed here; Word and PowerPoint were used instead.
- For slide 14, a fresh screenshot of `webapp/public` was taken with a throwaway local static server and headless Edge (both stopped immediately); it replaces the screenshot that showed the removed K-Means card.
- All numbers were read through one script module that logs value, source and the SUPERVISED_REPORT.md cross-check; this log is generated from that record.
- Second pass: run-level text replacements with python-docx and python-pptx on the four copies (exact-match asserted, one run at a time), validators and renders as in the first pass; a `check_pbix.py --help` call made by mistake during the review treated '--help' as a file name, printed NOT FOUND and wrote nothing (`faculty_evidence/powerbi/pbix_structure_check.md` still dated 13 Oct).
- Third pass: python-pptx and lxml on the deck copy only (picture removed, one shape inserted, one relationship dropped), the same validator and renderer; the PDF rename was a plain move within `D:\bigdata`, with the SHA-256 compared before and after.

