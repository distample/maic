# maic

maic is a local Python application for cleaning manga scans and converting
collections of page images into ebooks. Its interface opens in a browser and
runs on your computer at `http://127.0.0.1:5847` by default.

## Start

1. Install **CPython 3.14** and download or clone this repository. Extract the
   source ZIP before running it.
2. On Windows, double-click `start.bat` or run it from a terminal. For a new
   environment, `py -3.14` or `python` must point to Python 3.14.
3. On Linux or macOS, run `bash start.sh` from the project directory. Install
   Python 3.14 and venv support first.
4. Wait for the browser to open. Keep the launcher terminal open, and press
   **Ctrl+C** there to stop maic.

The first run creates `venv/` and installs pinned packages, including PyTorch.
It needs internet access and can take time. Later runs reuse the verified
environment. macOS installation has not been verified.

## First conversion

1. In **Conversion**, select a folder of page images.
2. Choose a separate output folder so the source remains untouched.
3. Select **EPUB maic**, **MOBI maic**, **KFX maic**, or **KFX + MOBI maic**, then start conversion.

These formats work with the files in this repository. For a first try,
use a folder of images; some archive formats require a separate 7-Zip tool.

| Output | Availability from this checkout |
| --- | --- |
| EPUB maic, MOBI maic | Included |
| KFX maic, KFX + MOBI maic | Included for supported image folders; maic builds the book and bundled kfxlib serializes the container |
| KCC-based formats | Require a separate Kindle Comic Converter installation/module |

For supported image folders, `KFX maic` and `KFX + MOBI maic` use maic's own
page and KFX-fragment generator without KCC or Kindle Previewer. The current
Python implementation uses the bundled GPLv3 kfxlib for Ion/YJ objects
and final KFX container encoding.

The Cleaning and Training sections are included. Pretrained model weights are
not bundled; features that use them need the appropriate model files. The
separate C++ desktop application is not part of this source distribution.

## Manual setup and diagnostics

After creating and activating a Python 3.14 virtual environment:

```sh
python _setup_torch.py --profile auto
python _setup_deps.py
python tools/bundled_modules.py --apply-patches
python run.py
```

Use `--profile cpu` with `_setup_torch.py` to select CPU explicitly. The
launchers run the full checks when the environment changes; to check it
manually without installing packages, run:

```sh
python _setup_torch.py --check
python _setup_deps.py --check
```

To use another port, pass `--port 5850` to the launcher. To open the optional
native window, install `requirements/gui.txt` and pass `--gui`.

Dependency versions are pinned in `requirements/`.

## Source layout

- `maic/`: Python backend and browser interface.
- `locale/`: interface translations.
- `requirements/`: pinned dependencies and optional groups.
- `run.py`, `start.bat`, `start.sh`: entry points.
- `modules/`: bundled kfxlib, public presets, and notes for optional KCC.

## License

The maic Python source is distributed under [GPLv3](LICENSE). Bundled
third-party code retains its original copyright and license notices; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
