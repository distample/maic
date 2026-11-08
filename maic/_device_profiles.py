"""Device screens maic knows without KCC.

The native writers do not run KCC over a single page, but they still ask it
one question: how big is the screen this book is for.  ``device_canvas``
resolves a profile name through ``kindlecomicconverter.image.ProfileData``,
which means a checkout with an empty ``modules/`` cannot build a volume in any
format -- including the three that otherwise need nothing installed.

This is the answer to that one question, for the devices maic actually
targets.  It is deliberately short.  Every screen here is a panel resolution
that can be checked against a real device, and
``tests/test_device_profiles.py`` asserts each one against KCC's own table on
any machine that has KCC, so the two cannot quietly disagree: the same source
must build the same book whether or not KCC happens to be installed.

Anything not listed is reached through **Other**, where the width and height
are typed in.  Guessing at the rest of KCC's table -- Kobo, reMarkable, a
decade of legacy Kindles -- would put numbers in a book that nobody has
checked, which is worse than not offering the device at all.
"""

# key -> (display name, (width, height))
#
# KPW12 is maic's own: the profile it injects into KCC's table in
# maic/kcc_patch.py rather than one KCC ships.  The rest are the panel
# resolutions of the devices the presets and the README are written around.
NATIVE_PROFILES = {
    "KPW12": ("Kindle Paperwhite 12", (1272, 1696)),
    "KPW5": ("Kindle Paperwhite 11", (1236, 1648)),
    # 1272x1696, not the 1264x1680 the Oasis has: caught by
    # tests/test_device_profiles.py against KCC's table, which is exactly
    # what that check is for.
    "KCS": ("Kindle Colorsoft", (1272, 1696)),
    "KO": ("Kindle Oasis 9/10", (1264, 1680)),
    "KS": ("Kindle Scribe 1/2", (1860, 2480)),
    "K11": ("Kindle 11", (1072, 1448)),
}

# The order the picker lists them in: newest and most common first, the same
# order the KCC-backed list uses for its "Kindle" group.
NATIVE_ORDER = ("KPW12", "KPW5", "KCS", "KO", "KS", "K11")

# What KCC calls the free-size profile.  The UI already has width and height
# fields behind it, so it is the escape hatch for every device not listed.
OTHER_KEY = "OTHER"


def native_profile_size(key):
    """The screen for *key*, or None when this table does not have it."""
    entry = NATIVE_PROFILES.get(str(key or "").strip())
    return entry[1] if entry else None


def native_profile_groups():
    """The same shape ``/api/convert/profiles`` returns from KCC's table.

    One group rather than KCC's five, because a group per manufacturer is only
    worth the space when there is more than one manufacturer in it.
    """
    entries = {}
    for key in NATIVE_ORDER:
        name, (width, height) = NATIVE_PROFILES[key]
        entries[name.replace(" ", "_").replace("/", "_")] = {
            "width": width,
            "height": height,
            # KCC carries a per-profile gamma; nothing in the native path reads
            # it, and 1.0 is "leave the page alone".
            "gamma": 1.0,
            "name": name,
            "profile_key": key,
        }
    entries["Other"] = {
        "width": 0,
        "height": 0,
        "gamma": 1.0,
        "name": "Other",
        "profile_key": OTHER_KEY,
    }
    return {"Kindle": entries}
