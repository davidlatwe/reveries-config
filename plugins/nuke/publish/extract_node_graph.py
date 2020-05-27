
import nuke
import pyblish.api
from avalon.nuke import lib
from reveries import utils


def walk_tree(node):
    yield node
    for input in node.dependencies():
        for n in walk_tree(input):
            yield n


class ExtractNodeGraph(pyblish.api.InstancePlugin):

    label = "Extract Node Graph"
    order = pyblish.api.ExtractorOrder + 0.1
    hosts = ["nuke"]
    families = [
        "reveries.write",
    ]

    def process(self, instance):
        node = instance[0]

        ext = "nknc" if nuke.env["nc"] else "nk"

        staging_dir = utils.stage_dir()
        filename = "%s.%s" % (instance.data["subset"], ext)
        outpath = "%s/%s" % (staging_dir, filename)

        instance.data["repr.nkscript._stage"] = staging_dir
        instance.data["repr.nkscript._files"] = [filename]
        instance.data["repr.nkscript.scriptName"] = filename
        instance.data["repr.nkscript.outputNode"] = node.fullName()

        with lib.maintained_selection():
            lib.reset_selection()
            for n in walk_tree(node):
                n["selected"].setValue(True)

            if node.Class() == "Write":
                # Swap image file path to published path bedore copy
                output = node["file"].value()
                node["file"].setValue(instance.data["publishedSeqPatternPath"])
                nuke.nodeCopy(outpath)
                node["file"].setValue(output)

            else:
                nuke.nodeCopy(outpath)

        # (TODO) The nuke script will be extracrted befroe write node being
        #   rendered if the target has set to Deadline.
        #   This extraction Should ALWAYS run after write node being rendered.
