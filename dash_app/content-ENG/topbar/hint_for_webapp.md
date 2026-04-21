## Usage tips

1. **First run**: click **Refresh data now** in the left rail, then **Save & Run** in the top bar to execute the full pipeline.
2. **Invest vs. research**: Invest shows explainer cards; research adds source traces, data indices, and methodology.
   Switching research retitles sidebar cards from “charts & methods brief” to “data, parameters & methodology detail.”
3. **Language toggle**: below Invest/Research, use **中 / EN** to append `?lang=chn` or `?lang=eng` and reload.
   Chinese copy lives under `dash_app/content-CHN/`; English copy under `dash_app/content-ENG/` with the same tree
   (`Inv/`, `Res-templates/`, etc.). With English selected, **only `content-ENG/` is read** for Markdown—there is no
   silent fallback to Chinese. Buttons, tabs, modals, P0–P4 phrases, accordion titles, left-rail hints, and overview
   cards are centralized in `all_labels.md`; long narratives are linked at the top of that file.
4. **Defense level**: the badge shows Level 0/1/2; click ↓ on the right to expand the defense-condition digest.
5. **Layout**: left rail = parameters, center = main charts, right rail = defense indicators.
6. **Custom assets**: P0 lets you edit the universe and weights—click **Apply** to recompute.
