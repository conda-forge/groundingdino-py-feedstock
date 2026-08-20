"""Strip an installed groundingdino down to its compiled extension.

The cuda output builds the whole wheel because that is the only way setup.py
will compile ``groundingdino._C``, but it must ship *only* the extension:
everything else is already owned by groundingdino-py-base, and two conda
packages claiming the same file is an error at install time.

Two things have to go, not one:

* every ``.py`` inside ``groundingdino/``
* the sibling ``groundingdino-*.dist-info/`` directory

The second is easy to miss -- it is not inside the package directory -- and
missing it is not harmless: base and cuda then collide on all eight of its
files, and the collision only appears when somebody installs both.

Usage: python prune_to_extension.py <site-packages>
"""

import sys
from pathlib import Path


def prune(site_packages: Path) -> None:
    if not site_packages.is_dir():
        raise SystemExit(f"not a directory: {site_packages}")

    pkg_dir = site_packages / "groundingdino"
    if not pkg_dir.is_dir():
        raise SystemExit(f"no groundingdino package in {site_packages}")

    kept = sorted(pkg_dir.glob("_C*.so"))
    if not kept:
        # Failing loudly matters here.  A silent miss would publish an empty
        # cuda package that installs cleanly and then falls back to the slow
        # path at run time, which is very hard to notice.
        raise SystemExit(f"no compiled extension found in {pkg_dir}")

    keep = {p.resolve() for p in kept}
    removed = 0

    for path in sorted(pkg_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            # rmdir only succeeds once the directory is empty, which is exactly
            # the condition for removing it.
            try:
                path.rmdir()
            except OSError:
                pass
        elif path.resolve() not in keep:
            path.unlink()
            removed += 1

    # The distribution metadata belongs to base, which installs the same eight
    # files under the same names.
    for dist_info in site_packages.glob("groundingdino-*.dist-info"):
        for path in sorted(dist_info.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
            else:
                path.unlink()
                removed += 1
        dist_info.rmdir()

    print(f"kept {[p.name for p in kept]}, removed {removed} file(s)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    prune(Path(sys.argv[1]))
