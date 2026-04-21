# Dash UI · Copy Index (Single Source of Truth)

> **Principle**: All front-end visible text is read from **this language’s** `content-CHN/` or
> `content-ENG/` tree; `dash_app/assets/*.json` is legacy compatibility only.
> After editing `.md`, **restart the Dash process** (in-memory cache).
>
> **Language switch**: top-left **中 / EN** → `?lang=chn` or `?lang=eng` → `app.py` layout calls
> `dash_app/services/copy.py::set_language()`. **No cross-folder fallback** between CHN and ENG;
> each language must have its own file.

---

## 1. Loading priority
```
content-CHN/<name>.md   (only when lang=chn)
content-ENG/<name>.md   (only when lang=eng)
  →  assets/<name>.json  (legacy; not the primary source)
```

All `get_*` helpers live in `dash_app/services/copy.py` and use `_get_copy(basename, key, default)`.
A same-named `.md` overrides the flat JSON.

---

## 2. Where does each .md control page?


| `.md` file | Control region | Python API used |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `figures_titles.md` | **The title of each chart** (gray bar above the chart) | `get_figure_title(key)` |
| `figures_hints.md` | **Small text below each chart** | `get_figure_hint(key)` |
| `all_labels.md` (formerly `topbar_labels.md`) | **Static copywriting for the whole site**: top bar (title / investment research / Chinese and English / Tab / button), main column P0–P4 (class label / diagnostic phrase / header / prompt / caption), research mode accordion title, Modal dialog box, left column `_aux_label` Auxiliary small text, overview card title; **hyperlinks to larger documents** listed at the top (such as `p0_aggregate_line.py` / `p1_stat_method.md`) | `get_topbar_label(key)` or equivalent `get_app_label(key)` |
| `sidebar_left.md` | Left column group subtitle + subtitle/auxiliary label within the group (merged levels; H2 = subtitle, H3 = subtitle/auxiliary label) | `get_sidebar_left_title(key)` · `get_sidebar_left_label(key)` |
| `sidebar_left_params_explanations.md` | Explanation of the left column parameter question mark button after expansion | `get_param_explanation(key)` |
| `kronos_hints.md` | Kronos weight status prompts | `get_kronos_hint(key)` |
| `status_messages.md` | **Scattered runtime prompts, placeholders, and button text** (including the 4-part subtitles of Fig4.1) | `get_status_message(key)` |
| `defense_intro.md` | Three columns expanded in the top bar Level 0/1/2 Introduction | `get_defense_intro()` |
| `project_intro.md` | "Research Project Overview" text | `get_project_intro()` |
| `phase0_tab_intro.md` / `phase1_intro.md` / ... / `phase4_intro.md` | The top blurb of each Phase | `get_phase_intro(0..4)` |
| `Res-templates/FigX.*-Res.md` / `Inv/FigX.*-Inv.md` / `Res-templates/Fig0.1-Res.md` ... | The **longest explanation card** for a single picture (including the `## Defense-Tag` paragraph). Research mode uses `Res-templates/` as the only source of truth; `Res/` is the offline snapshot product of `dash_app/utilities/md_sync.py --write-md` and is not read by the runtime. | `dash_app/render/explain/_loaders.py::load_figx_template` / `load_fig4_template` / `load_defense_tag_text`, `build_figxN_explain_body` |
| `defense_reasons.md` | Summary of defense conditions (general list) | Top bar expansion area |
| `hint_for_webapp.md` | Top bar "Webapp running and usage tips" pop-up window | `get_md_text('hint_for_webapp.md')` |
| `Methodology_constraints.md` | Methodology limitations block | Corresponding footer |


---

## 3. MD format rules (only one copy, do not change it again)

Simple key-value (most files use this):
```md
# Feel free to add explanatory comments (ignored by the system)
> Quoted blocks are also ignored

key_name: "A piece of Chinese copy that can contain spaces and punctuation"
another_key: "value"
```**Allow**:

- Add any `#` title / `>` quote block to the file header for comment
- `key: value` insert blank lines in the middle
- Do not write `---` fence (the remaining single `---` from the old version is also compatible)
- Values in double quotes `"…"`, single quotes `'…'` or unquoted

**Not allowed**:

- Add `##` in front of key (this is a historical pitfall, the latest parser will **automatically strip it**, but please do not write it new)
- key is in Chinese (must be `[A-Za-z_][A-Za-z0-9_\-\.]`*)

Nested structures (`defense_intro.md` kind): Flatten keys with underscores, for example `level2_title` / `level2_item_1`.

---

## 4. Modification process (minimum runnable case)

1. Open the corresponding `.md` and change the text within the quotation marks.
2. Save.
3. **Restart Dash process** (with in-process cache `_md_cache`).
4. Hard refresh the browser (Ctrl+F5).

Quickly verify locally whether a key has been read (without starting Dash):
```bash
cd "Final_gp02-main 4.18 night"
python -c "from dash_app.figure_caption_service import get_status_message; print(get_status_message('fig41_section2_title'))"
```---

## 5. Fig4.1 / FigX.2 / FigX.4 bug description

### Fig4.1 Not displayed

The current design is a **four-part panel** (see `dashboard_face_render.py::_p4_experiments_stack_block` and this directory `Fig4.1-Res.md` for details), relying on the `phase3.defense_validation.fig41_verify` field.

- If the existing `data.json` is an old version: **The pipeline must be re-run** (click "Save and Run" or `/api/refresh` in the sidebar).
- If the new version pipeline is run but still empty: check the return of `research/post_alarm_realized_metrics.py::build_fig41_verify_bundle`, maybe `test_st_series` is empty or the reference day mapping fails.

The placeholder text for "No Daily Returns Available"/"No Data" in the chart area now comes entirely from `status_messages.md`**:

- `fig41_empty_daily_returns`
- `fig41_empty_std_by_k`

### FigX.2 Structural Entropy / FigX.4 Credibility Style Issues

The DOM structure generated by `metric_rails.py` is healthy and the CSS is in `assets/custom.css`. If you find an abnormality in the style, please provide a **screenshot** and indicate:

- The width of the color block is wrong → flex allocation problem of `defense-rgy-seg`
- Wrong label position → `left` percentage of `defense-tau-anno`
- Wrong text color → Dark mode color variable of `metric-rail-title`

### Title is not updated with .md

**This problem has been fixed**. Root cause: The parser requires `---` first and last fences, old `figures_titles.md` only has the beginning. The new parser tolerates arbitrary formats and reads `.md` first.

---

## 6. Deprecated JSON files

The following files remain in `assets/` as a fallback, do not edit them again (changes will not take effect):

- `figures_titles.json`
- `figures_hints.json`
- `topbar_labels.json` (`.md` has been renamed to `all_labels.md`; this JSON is reserved for final information only)
- `sidebar_left_titles.json`
- `sidebar_left_labels.json`
- `sidebar_left_params_explanations.json`
- `kronos_hints.json`
- `status_messages.json`
- `defense_intro.json`
- `project_intro.json`
- `P{0..4}_intro.json`
- `figure_captions.json` (**Exception**: still in use, complex structure not suitable for md, not migrated yet)