import pyblish.api


class CollectComment(pyblish.api.ContextPlugin):
    """Receive comment from Pyblish GUI comment box

    This initialize "comment" field in context for GUI input.

    If using Pyblish-Lite, this plug-ins will trigger the GUI
    comment dialog box per default.

    """

    label = "Receive Publish Comment"
    order = pyblish.api.CollectorOrder - 0.49

    def process(self, context):
        context.data["comment"] = ""
