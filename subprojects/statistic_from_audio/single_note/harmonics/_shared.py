# router:skip
"""Shared WAV-picking/loading helper for the statistic_from_audio scripts."""

import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def _find_project_root(start):
    for parent in (start, *start.parents):
        if (parent / "main.py").exists() and (parent / "subprojects").exists():
            return parent
    raise RuntimeError("Could not find the project root (expected main.py + subprojects/ nearby)")


_PROJECT_ROOT = _find_project_root(Path(__file__).resolve())
_RECORDINGS_DIR = _PROJECT_ROOT / "Recordings"

sys.path.insert(0, str(_PROJECT_ROOT))
from main import choose, choose_multi  # reuse the router's own menus


def _list_subdirs(directory):
    return sorted(
        (p for p in directory.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))),
        key=lambda p: p.name.lower(),
    )


def _list_wavs(directory):
    return sorted(directory.glob("*.wav"), key=lambda p: p.name.lower())


def _require_recordings_dir():
    if not _RECORDINGS_DIR.is_dir():
        print(f"No '{_RECORDINGS_DIR.name}/' folder found at {_PROJECT_ROOT}.")
        print("Create it and drop some subfolders of .wav files inside.")
        sys.exit(1)


def _group_wavs_by_subdir(directory):
    """Look at directory's immediate subfolders that directly hold WAV
    files (e.g. pp/, mf/, ff/), and group same-named files across them
    (e.g. piano_single_C4.wav in each). Returns (groups, subdir_names)
    where groups maps filename -> {subdir_name: path}, limited to
    filenames present in 2+ of those subfolders."""
    per_dir = {}
    for d in _list_subdirs(directory):
        wavs = _list_wavs(d)
        if wavs:
            per_dir[d.name] = {w.name: w for w in wavs}
    if len(per_dir) < 2:
        return {}, []

    all_names = set()
    for files in per_dir.values():
        all_names |= set(files.keys())

    groups = {}
    for name in sorted(all_names):
        present = {dyn: files[name] for dyn, files in per_dir.items() if name in files}
        if len(present) >= 2:
            groups[name] = present
    return groups, sorted(per_dir.keys())


def select_wav():
    """Browse Recordings/ folder by folder (same UI as the router itself)
    down to a single WAV file."""
    _require_recordings_dir()
    directory = _RECORDINGS_DIR
    while True:
        subdirs = _list_subdirs(directory)
        wavs = _list_wavs(directory)
        if not subdirs and not wavs:
            print(f"Nothing found in {directory.relative_to(_PROJECT_ROOT)}.")
            sys.exit(1)

        entries = [(d.name + "/", "dir", d) for d in subdirs] + [(w.name, "file", w) for w in wavs]
        items = [label for label, _, _ in entries]
        title = str(directory.relative_to(_PROJECT_ROOT))
        result = choose(title, items)

        if result == "quit":
            sys.exit(0)
        elif result == "back":
            if directory != _RECORDINGS_DIR:
                directory = directory.parent
        elif isinstance(result, int):
            _, kind, path = entries[result]
            if kind == "dir":
                directory = path
            else:
                return path


def select_wavs():
    """Browse Recordings/ folder by folder down to whichever folder holds
    the files you want, then multi-select among that folder's WAV files
    (Space toggles, 'a' toggles all, Enter confirms; plain fallback takes
    comma-separated numbers/ranges like '1,3,5-8', or 'all').

    If the current folder's immediate subfolders each hold same-named WAV
    files (e.g. pp/mf/ff each holding piano_single_C4.wav), an extra entry
    lets you multi-select by filename and pulls every matching file from
    every one of those subfolders at once -- e.g. picking
    "piano_single_C4.wav" grabs it from pp, mf, and ff in one go, so you
    don't have to run compare three times to see all dynamics of one note."""
    _require_recordings_dir()
    directory = _RECORDINGS_DIR
    while True:
        subdirs = _list_subdirs(directory)
        wavs = _list_wavs(directory)
        groups, group_dirs = _group_wavs_by_subdir(directory)
        if not subdirs and not wavs:
            print(f"Nothing found in {directory.relative_to(_PROJECT_ROOT)}.")
            sys.exit(1)

        entries = [(d.name + "/", "dir", d) for d in subdirs]
        items = [label for label, _, _ in entries]

        pick_here_index = None
        if wavs:
            pick_here_index = len(items)
            items.append(f"[ Select from the {len(wavs)} file(s) here ]")

        pick_group_index = None
        if groups:
            pick_group_index = len(items)
            items.append(f"[ Select notes across {', '.join(group_dirs)} here ]")

        title = str(directory.relative_to(_PROJECT_ROOT))
        result = choose(title, items)

        if result == "quit":
            sys.exit(0)
        elif result == "back":
            if directory != _RECORDINGS_DIR:
                directory = directory.parent
        elif isinstance(result, int):
            if result == pick_here_index:
                labels = [w.name for w in wavs]
                picked = choose_multi(f"Pick recordings in {title}", labels)
                if picked == "quit":
                    continue  # cancelled the file picker, stay in folder nav
                return [wavs[i] for i in picked]
            if result == pick_group_index:
                names = sorted(groups.keys())
                picked = choose_multi(f"Pick notes to compare across {', '.join(group_dirs)}", names)
                if picked == "quit":
                    continue
                paths = []
                for i in picked:
                    paths.extend(groups[names[i]].values())
                return paths
            _, kind, path = entries[result]
            directory = path


def select_folder():
    """Browse Recordings/ folder by folder and return whichever folder you
    land on. An extra "[ Use this folder ]" entry lets you stop at any
    level instead of having to descend all the way to a leaf folder --
    e.g. land on "Sample Recordings" itself to grab everything under it
    (pp/mf/ff and all), not just one dynamic's worth of files."""
    _require_recordings_dir()
    directory = _RECORDINGS_DIR
    while True:
        subdirs = _list_subdirs(directory)
        entries = [(d.name + "/", "dir", d) for d in subdirs]
        items = [label for label, _, _ in entries]
        use_here_index = len(items)
        items.append("[ Use this folder ]")

        title = str(directory.relative_to(_PROJECT_ROOT))
        result = choose(title, items)

        if result == "quit":
            sys.exit(0)
        elif result == "back":
            if directory != _RECORDINGS_DIR:
                directory = directory.parent
        elif isinstance(result, int):
            if result == use_here_index:
                return directory
            _, _, path = entries[result]
            directory = path


def _read_as_mono_float(path):
    sample_rate, data = wavfile.read(path)

    if data.ndim > 1:
        data = data.mean(axis=1)

    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float64) / np.iinfo(data.dtype).max
    else:
        data = data.astype(np.float64)

    return sample_rate, data


def load_wav():
    """Let the user browse Recordings/ down to one WAV file and load it as
    float64 mono samples in [-1, 1]."""
    path = select_wav()
    sample_rate, data = _read_as_mono_float(path)
    return sample_rate, data, path


def load_wavs():
    """Multi-file version of load_wav() -- returns a list of
    (sample_rate, data, path) tuples for the user's selection."""
    paths = select_wavs()
    return [(*_read_as_mono_float(path), path) for path in paths]
