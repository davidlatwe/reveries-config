
import pyblish.api


class CollectWriteRange(pyblish.api.InstancePlugin):

    label = "Write Range"
    order = pyblish.api.CollectorOrder
    hosts = ["nuke"]
    families = [
        "reveries.write"
    ]

    def process(self, instance):
        context = instance.context
        write = instance[0]

        if write["use_limit"].value():
            first = int(write["first"].value())
            last = int(write["last"].value())

        else:
            first = context.data["startFrame"]
            last = context.data["endFrame"]

        instance.data["startFrame"] = first
        instance.data["endFrame"] = last
        instance.data["byFrameStep"] = 1

        instance.data["label"] += " [%d-%d]" % (first, last)

        self.log.info("Write range: %d-%d" % (first, last))
