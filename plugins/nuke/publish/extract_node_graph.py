
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

    def extract_nkscript(self, instance):
        node = instance[0]

        packager = instance.data["packager"]
        package_path = packager.create_package()

        ext = "nknc" if nuke.env["nc"] else "nk"

        fname = packager.file_name(extension=ext)
        fpath = os.path.join(package_path, fname)

        with lib.maintained_selection():
            lib.reset_selection()
            for n in walk_tree(node):
                n["selected"].setValue(True)

            if node.Class() == "Write":
                # Swap image file path to published path bedore copy
                output = node["file"].value()
                node["file"].setValue(instance.data["publishedSeqPatternPath"])
                nuke.nodeCopy(fpath)
                node["file"].setValue(output)

            else:
                nuke.nodeCopy(fpath)

        packager.add_data({
            "outputNode": node.fullName(),
            "scriptName": fname,
        })
