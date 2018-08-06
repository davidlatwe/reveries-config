import sys
import os
import subprocess

import reveries.base as base


def open(filepath):
    """Open file with system default executable"""
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


class PlayImageSequence(base.EntryFileLoader):
    """Open Image Sequence with system default"""

    label = "Play sequence"
    order = -10
    icon = "play-circle"
    color = "orange"

    families = [
        "reveries.camera",
        "reveries.playblast",
    ]

    representations = base.repr_obj_list([
        ("PNGSequence", "png"),
        ("QuickTime", "mov"),
    ])

    def load(self, context, name, namespace, data):

        directory = self.repr_dir
        from avalon.vendor import clique

        pattern = clique.PATTERNS["frames"]
        files = os.listdir(directory)
        collections, remainder = clique.assemble(files,
                                                 patterns=[pattern],
                                                 minimum_items=1)

        assert not remainder, ("There shouldn't have been a remainder for "
                               "'%s': %s" % (directory, remainder))

        seqeunce = collections[0]
        first_image = list(seqeunce)[0]
        filepath = os.path.normpath(os.path.join(directory, first_image))

        self.log.info("Opening : {}".format(filepath))

        open(filepath)
