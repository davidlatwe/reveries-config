import sys
import os
import subprocess

import avalon.api

from reveries.plugins import PackageLoader


def open(filepath):
    """Open file with system default executable"""
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


class PlayImageSequence(PackageLoader, avalon.api.Loader):
    """Open Image Sequence with system default"""

    label = "Play sequence"
    order = -10
    icon = "play-circle"
    color = "orange"

    families = [
        "reveries.imgseq",
    ]

    representations = [
        "imageSequence",
    ]

    def load(self, context, name, namespace, data):

        from avalon.vendor import clique

        directory = self.package_path

        files = os.listdir(directory)
        collections, remainder = clique.assemble(files,
                                                 minimum_items=1)

        assert not remainder, ("There shouldn't have been a remainder for "
                               "'%s': %s" % (directory, remainder))

        seqeunce = collections[0]
        first_image = list(seqeunce)[0]
        filepath = os.path.normpath(os.path.join(directory, first_image))

        self.log.info("Opening : {}".format(filepath))

        open(filepath)


class OpenImageSequence(PackageLoader, avalon.api.Loader):
    """Open Image Sequence with system default"""

    label = "Open sequence"
    order = -10
    icon = "folder-open"
    color = "orange"

    families = [
        "reveries.imgseq",
    ]

    representations = [
        "imageSequence",
        "imageSequenceSet",
    ]

    def load(self, context, name, namespace, data):
        directory = self.package_path

        self.log.info("Opening : {}".format(directory))

        open(directory)
