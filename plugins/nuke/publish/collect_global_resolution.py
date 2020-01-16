
import pyblish.api


class CollectResolution(pyblish.api.ContextPlugin):

    label = "Project Resolution"
    order = pyblish.api.CollectorOrder - 0.1
    hosts = ["nuke"]

    def process(self, context):
        import nuke

        root = nuke.Root()
        context.data["resolution"] = (root.width(), root.height())
