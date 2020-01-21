
import os
import nuke
import pyblish.api
from avalon.nuke import lib
from reveries.plugins import PackageExtractor


def walk_tree(node):
    yield node
    for input in node.dependencies():
        for n in walk_tree(input):
            yield n


class ExtractNodeGraph(PackageExtractor):

    label = "Extract Node Graph"
    order = pyblish.api.ExtractorOrder + 0.1
    hosts = ["nuke"]

    families = [
        "reveries.write",
    ]

    representations = [
        "nkscript",
    ]

    targets = ["localhost"]

    def extract_nkscript(self, packager):
        node = self.member[0]

        package_path = packager.create_package()

        ext = "nknc" if nuke.env["nc"] else "nk"

        fname = packager.file_name(extension=ext)
        fpath = os.path.join(package_path, fname)

        with lib.maintained_selection():
            lib.reset_selection()
            for n in walk_tree(node):
                n["selected"].setValue(True)

            nuke.nodeCopy(fpath)

        packager.add_data({
            "outputNode": node.fullName(),
            "scriptName": fname,
        })
