
import pyblish.api
import os


class CollectWritePath(pyblish.api.InstancePlugin):

    label = "Write Path"
    order = pyblish.api.CollectorOrder
    hosts = ["nuke"]
    families = [
        "reveries.write"
    ]

    def process(self, instance):
        write = instance[0]
        outpath = write["file"].value()
        outpath = os.path.normpath(outpath).replace("\\", "/")

        instance.data["outputPath"] = outpath
