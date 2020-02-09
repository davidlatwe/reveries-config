import pyblish.api


class CollectNukeVersion(pyblish.api.ContextPlugin):
    """Get Nuke version number"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Nuke Version"
    hosts = ["nuke"]

    def process(self, context):
        import nuke

        context.data["nukeVersion"] = "%s.%s" % (nuke.NUKE_VERSION_MAJOR,
                                                 nuke.NUKE_VERSION_MINOR)
