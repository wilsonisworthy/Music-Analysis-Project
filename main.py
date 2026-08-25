#!/usr/bin/env python3
"""Interactive router: browse subprojects/ and run whichever one you pick.

Arrow keys (or w/s) to move, Enter to select, Left/Backspace to go back,
Esc/q to quit. Falls back to numbered input when stdin isn't a real
terminal (e.g. piped input).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBPROJECTS_DIR = ROOT / "subprojects"

# A script opts out of the menu by starting its filename with "." or "_",
# or by putting a "# router:skip" comment in its first few lines.
SKIP_MARKER_RE = re.compile(r"#\s*router\s*:\s*skip", re.IGNORECASE)
SKIP_MARKER_SCAN_LINES = 20


def _enable_ansi_on_windows():
    if os.name != "nt":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING


def read_key():
    """Block for one keypress, return 'up'/'down'/'enter'/'back'/'quit'/None."""
    if os.name == "nt":
        import msvcrt

        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            return {b"H": "up", b"P": "down", b"K": "back", b"M": "enter"}.get(ch2)
        if ch in (b"\r", b"\n"):
            return "enter"
        if ch == b"\x08":
            return "back"
        if ch == b"\x1b":
            return "quit"
        if ch in (b"q", b"Q"):
            return "quit"
        if ch in (b"w", b"W"):
            return "up"
        if ch in (b"s", b"S"):
            return "down"
        return None
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                rest = sys.stdin.read(2)
                if rest == "[A":
                    return "up"
                if rest == "[B":
                    return "down"
                if rest == "[D":
                    return "back"
                if rest == "[C":
                    return "enter"
                return "quit"
            if ch in ("\r", "\n"):
                return "enter"
            if ch == "\x7f":
                return "back"
            if ch in ("q", "Q"):
                return "quit"
            if ch in ("w", "W"):
                return "up"
            if ch in ("s", "S"):
                return "down"
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clear_screen():
    print("\033[2J\033[H", end="")


def render_menu(title, items, selected):
    clear_screen()
    print(title)
    print("-" * max(len(title), 40))
    for i, label in enumerate(items):
        if i == selected:
            print(f"\033[7m> {label}\033[0m")
        else:
            print(f"  {label}")
    print()
    print("Up/Down move   Enter select   Left/Backspace back   Esc/q quit")


def choose_plain(title, items):
    """Numbered-input fallback for non-interactive stdin."""
    clear_screen()
    print(f"\n{title}")
    print("-" * max(len(title), 40))
    for i, label in enumerate(items, start=1):
        print(f"  {i}. {label}")
    print("  b. Back")
    print("  q. Quit")
    try:
        choice = input("\nSelect: ").strip().lower()
    except EOFError:
        return "quit"
    if choice in ("q", "quit"):
        return "quit"
    if choice in ("b", "back"):
        return "back"
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        return int(choice) - 1
    print("Invalid choice, try again.")
    return choose_plain(title, items)


def choose(title, items):
    """Menu over items (list of str). Returns index, 'back', or 'quit'."""
    # Git Bash/MSYS ptys often report isatty() True but don't give msvcrt a
    # real console handle, so arrow-key reads there just hang.
    if not sys.stdin.isatty() or os.environ.get("MSYSTEM"):
        return choose_plain(title, items)

    selected = 0
    while True:
        render_menu(title, items, selected)
        key = read_key()
        if key == "up":
            selected = (selected - 1) % len(items)
        elif key == "down":
            selected = (selected + 1) % len(items)
        elif key == "enter":
            return selected
        elif key == "back":
            return "back"
        elif key == "quit":
            return "quit"


def list_subdirs(directory):
    return sorted(
        (p for p in directory.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))),
        key=lambda p: p.name.lower(),
    )


def has_skip_marker(script):
    try:
        with script.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in range(SKIP_MARKER_SCAN_LINES):
                line = f.readline()
                if not line:
                    break
                if SKIP_MARKER_RE.search(line):
                    return True
    except OSError:
        pass
    return False


def list_scripts(directory):
    return sorted(
        (
            p
            for p in directory.glob("*.py")
            if not p.name.startswith((".", "_")) and not has_skip_marker(p)
        ),
        key=lambda p: p.name.lower(),
    )


def run_script(script):
    clear_screen()
    print(f"--- Running {script.relative_to(ROOT)} ---\n")
    subprocess.run([sys.executable, str(script)], cwd=script.parent)
    print(f"\n--- Finished {script.relative_to(ROOT)} ---")
    if sys.stdin.isatty() and not os.environ.get("MSYSTEM"):
        print("Press any key to continue...")
        read_key()
    else:
        input("Press Enter to continue...")
    clear_screen()


def navigate(directory):
    while True:
        subdirs = list_subdirs(directory)
        scripts = list_scripts(directory)

        if not subdirs and not scripts:
            clear_screen()
            print(f"Nothing found in {directory.relative_to(ROOT)} (no subfolders, no runnable .py files).")
            return

        entries = [(d.name + "/", "dir", d) for d in subdirs] + [
            (s.name, "file", s) for s in scripts
        ]
        items = [label for label, _, _ in entries]

        label = "." if directory == SUBPROJECTS_DIR else str(directory.relative_to(ROOT))
        result = choose(label, items)

        if result == "quit":
            clear_screen()
            sys.exit(0)
        elif result == "back":
            if directory != SUBPROJECTS_DIR:
                return
        elif isinstance(result, int):
            _, kind, path = entries[result]
            if kind == "dir":
                navigate(path)
            else:
                run_script(path)


def main():
    _enable_ansi_on_windows()
    if not SUBPROJECTS_DIR.exists():
        print(f"No '{SUBPROJECTS_DIR.name}/' directory found. Create it and add subprojects.")
        sys.exit(1)
    navigate(SUBPROJECTS_DIR)


if __name__ == "__main__":
    main()
