# Development Setup

This page summarises how to run NeoArch from source. The canonical, always
up-to-date version lives in the repository:
[docs/development/setup.md](https://github.com/sanjayadanushka712/NeoArch/blob/main/docs/development/setup.md).

## Prerequisites

- Python 3.8 or newer
- Git
- PyQt6 and its system dependencies (`libegl1`, `libgl1`, `libglib2.0-0`,
  `libgtk-3-0`, `libxcb-*`, `libxkbcommon-x11-0`, `libdbus-1-3`,
  `libfontconfig1`, `libfreetype6`, `libasound2`, `libpulse0`, `xvfb`)

## Quick start

```bash
git clone https://github.com/sanjayadanushka712/NeoArch.git
cd Neoarch
git checkout dev

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python Neoarch.py          # GUI
python -m neoarch.cli --help   # headless CLI
```

## Running the tests

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests -q
```

The offscreen platform keeps the suite runnable on a headless machine or in
CI.

## Branching model

| Branch | Purpose |
|---|---|
| `dev` | Day-to-day development; pull requests target this branch |
| `main` | Released code; receives merges from `dev` at release time |
| `v3.0`, `v2.0-deprecated`, `v1.0-deprecated` | Frozen historical branches |

Releases are cut by merging `dev` into `main`, tagging `vX.Y.Z`, and merging
`main` back into `dev`.

## See also

- [Contributing](Contributing.md)
- [Architecture](Architecture.md)
