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

Currently: `Recordings/Sample Recordings/` holds 48 single isolated piano
notes (`piano_single_<note>.wav`) — no pedal, no other notes overlapping —
pulled from the University of Iowa Electronic Music Studios instrument
samples (theremin.music.uiowa.edu), mezzo-forte dynamic, trimmed to attack +
decay. Covers all 12 notes across 4 octaves (2-5), i.e. C2 through B5.
`Recordings/Audio Recordings/` is currently empty -- kept as a separate
destination (e.g. for your own recordings, as opposed to downloaded
sample-library notes).

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

