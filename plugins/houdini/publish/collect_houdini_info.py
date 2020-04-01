
import pyblish.api


class CollectHoudiniInfo(pyblish.api.ContextPlugin):
    """Collect Houdini version into context"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "About Houdini .."
    hosts = ["houdini"]

    def process(self, context):
        import hou

        houdini_version = hou.applicationVersionString()
        context.data["houdiniVersion"] = houdini_version.rsplit(".", 1)[0]
