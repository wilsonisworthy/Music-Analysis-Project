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

## Audio Recordings

Drop `.wav` files into `Audio Recordings/` at the project root. Scripts under
`subprojects/statistic_from_audio/` (and any new ones built on its `_shared.py`
helper) list files from that folder with the same arrow-key/numbered menu as
the router, instead of asking for a file path.

