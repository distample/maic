# Licensing and third-party notices

Except where noted below, the maic Python source and interface in this
repository are distributed under GNU General Public License version 3.
The full license text is in [LICENSE](LICENSE).

## kfxlib

`modules/kfxlib/` contains a reviewed local snapshot of the KFX Output
plugin's `kfxlib` by John Howell (copyright 2016–2026), marked GPL v3 in
its source files. The full GPLv3 text is also in
[modules/kfxlib/COPYING](modules/kfxlib/COPYING).

Source project: [KFX Output plugin by John Howell](https://www.mobileread.com/forums/showthread.php?t=272407).
The local `kfxlib/version.py` reports `20260822`; the exact upstream commit
for this snapshot has not been established. The reviewed Python file hashes
are recorded in `requirements/bundled-modules.json`. This snapshot has a
Python 3.14 compatibility change in `utilities.py`, marked there on 2026-10-26: `locale.getdefaultlocale()`
was replaced with `locale.getencoding()`; the manifest records its source hash
and replacement.

## Libraries included inside kfxlib

- `calibre-plugin-modules/pypdf/`: pypdf 6.16.1, BSD-3-Clause. Its license
  is at [modules/kfxlib/calibre-plugin-modules/pypdf/LICENSE](modules/kfxlib/calibre-plugin-modules/pypdf/LICENSE).
- `calibre-plugin-modules/typing_extensions.py`: typing_extensions 4.16.0,
  PSF-2.0. Its license is at
  [modules/kfxlib/calibre-plugin-modules/LICENSE.typing_extensions](modules/kfxlib/calibre-plugin-modules/LICENSE.typing_extensions).

The source files retain their original copyright notices.
