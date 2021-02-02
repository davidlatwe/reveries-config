
import pyblish.api


class CollectDeadlineExcluded(pyblish.api.ContextPlugin):

    order = pyblish.api.CollectorOrder - 0.29
    hosts = ["maya"]
    label = "Deadline Excluded"

    targets = ["deadline"]

    def process(self, context):

        supported = [
            "reveries.pointcache",
            "reveries.standin",
            "reveries.rsproxy",
            "reveries.camera",
            "reveries.renderlayer",
        ]

        excluded = list()
        for instance in list(context):
            if instance.data["family"] not in supported:
                excluded.append(instance)
                context.remove(instance)

        for instance in excluded:
            instance.data["publish"] = False
            instance.data["optional"] = False
            instance.data["category"] = "Deadline Not Supported"

            context.append(instance)
