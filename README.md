# Music Analysis Project

Run `python main.py` and pick a subproject from the menu. It browses the
`subprojects/` folder tree, lets you descend into nested folders, and runs
whichever one you land on.

## Adding a subproject

Create a folder anywhere under `subprojects/` (nesting is fine). Any `.py`
file directly inside it shows up in the menu as something you can run:

```python
def main():
    ...

if __name__ == "__main__":
    main()
```

It'll show up in the router automatically — nothing else to register.

To keep a file out of the menu (a helper module, config, etc.), either:
- prefix the filename with `.` or `_` (e.g. `_utils.py`), or
- add a `# router:skip` comment in the file's first ~20 lines.

The same underscore/dot rule applies to folders — `_scratch/` won't be
browsed.

## Recordings

Drop `.wav` files anywhere under `Recordings/` at the project root (nesting
is fine). Scripts under `subprojects/statistic_from_audio/` browse that
folder tree the same folder-by-folder way the router itself browses
`subprojects/` -- descend into a subfolder, land on its files.

Currently: `Recordings/Sample Recordings/` holds single isolated piano notes
(`piano_single_<note>.wav`) — no pedal, no other notes overlapping — pulled
from the University of Iowa Electronic Music Studios instrument samples
(theremin.music.uiowa.edu), trimmed to attack + decay. Covers all 12 notes
across 4 octaves (2-5), i.e. C2 through B5, split into three dynamic-level
subfolders played at different force: `pp/` (pianissimo, softest), `mf/`
(mezzo-forte), `ff/` (fortissimo, loudest) -- 144 files total, same 48 notes
at each of the three dynamics, useful for correlating strike force with
attack/decay/brightness. `Recordings/Audio Recordings/` is currently empty
-- kept as a separate destination (e.g. for your own recordings, as opposed
to downloaded sample-library notes).

## Subproject layout

`subprojects/statistic_from_audio/single_note/` groups the two
single-recording analyses -- `amplitude/` (attack/decay envelope) and
`harmonics/` (timbre-over-time spectrogram + brightness) -- each still run
individually, one file at a time. `compare/` and `csv_export/` (below)
work across many recordings at once and sit alongside `single_note/`.

## Cross-analysis across recordings

`subprojects/statistic_from_audio/compare/` browses down to a folder and
multi-selects files inside it (arrow-key mode: Space to toggle a file, `a`
to toggle all, Enter to confirm; plain fallback: comma-separated numbers/
ranges like `1,3,5-8`, or `all`), then asks which analysis to run --
Amplitude, Harmonics, or Both. Each selected recording gets its own row of
plot(s), sorted by pitch when the filename ends in a note name (e.g.
`..._C4.wav`) -- the amplitude envelope and/or the harmonics spectrogram,
side by side, exactly like running the individual scripts, just all on one
page instead of one file at a time. A plain text table of the raw attack/
decay/brightness numbers prints below the plots.

If the folder you land on has sibling subfolders that each hold the same
filenames (like `pp/`, `mf/`, `ff/` under Sample Recordings), an extra
`[ Select notes across pp, mf, ff here ]` entry appears -- pick a note once
and it pulls that note from all three dynamics in one go, instead of
running compare three separate times. Rows for the same note are grouped
together and ordered softest-to-loudest, labeled e.g. `C4 (pp)` /
`C4 (mf)` / `C4 (ff)`, so you can read attack/decay/brightness across
force levels straight down the table.

## Batch export to CSV

`subprojects/statistic_from_audio/csv_export/` browses down to a folder
(an extra `[ Use this folder ]` entry lets you stop at any level, not just
a leaf) and runs every `.wav` file found under it, recursively, through
the same attack/decay + brightness analysis -- e.g. point it at
`Sample Recordings/` and it'll walk `pp/`, `mf/`, `ff/` and every note in
each. No plots, no interactive picking of individual files -- it just
prints progress as it goes and writes one row per file (filename, parent
folder, note, octave, sample rate, duration, attack time, decay time,
brightness start/end, brightness change %, plus how many STFT frames were
actually trusted above the noise floor vs. total) to a timestamped CSV
under `Results/` at the project root, meant for digging into later (e.g.
fitting how attack/decay/brightness relate to strike force across all 144
notes) rather than reading by eye.

Brightness columns can come back blank for quiet (pp) recordings -- the
same 15dB-above-noise-floor gate the other tools use means a note that
never gets loud enough relative to background noise has no trustworthy
brightness reading at all, not just a noisy one. The
`brightness_frames_trusted` / `brightness_frames_total` columns show how
marginal each measurement was (e.g. 6/260 frames trusted is a thin
reading even when a number is present) so blank/thin rows can be told
apart from solid ones during analysis instead of silently averaged in.

## Finding trends across a CSV

`subprojects/statistic_from_audio/Analysis/` loads a CSV from `Results/`
(auto-picks it if there's only one, otherwise asks which, most recent
first) and plots attack time, decay time, and brightness change all
against dynamic/force level (pp/mf/ff or whatever groups are present) side
by side. Each note gets its own thin line across the dynamics (colored by
octave, so register effects are visible), plus a bold linear fit and
Pearson correlation per metric printed to the terminal and drawn on the
plot -- a first-pass "equation" for how each property scales with strike
force. Needs at least two dynamic levels in the CSV to say anything about
a trend; requires `csv_export` to have been run first.

