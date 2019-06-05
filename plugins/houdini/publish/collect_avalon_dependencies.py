
import pyblish.api


class CollectAvalonDependencies(pyblish.api.ContextPlugin):
    """Collect Avalon dependencies from root containers
    """

    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]
    label = "Avalon Dependencies"

    def process(self, context):
        for instance in context:
            instance.data["dependencies"] = dict()
            # (TODO) Finding `ObjectMerge` node in the network,
            #        look for containerized sop path.
