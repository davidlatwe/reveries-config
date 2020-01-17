
import pyblish.api
import re
import os


def convert_frame_format(path):
    """Convert format like '%04d' into '####' padding format"""
    head, tail = os.path.split(path)

    def replace(match):
        count = int(match.group(2))
        return match.group(1) + "#" * count + match.group(3)

    tail = re.sub("(.*)%([0-9]*)d(.*)", replace, tail)

    return head + "/" + tail


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
        outpath = convert_frame_format(outpath)

        instance.data["outputPath"] = outpath
        instance.data["fileExt"] = os.path.splitext(outpath)[-1]

        self.log.info("Write to: %s" % outpath)
