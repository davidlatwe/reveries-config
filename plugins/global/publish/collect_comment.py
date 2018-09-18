import pyblish.api


class CollectComment(pyblish.api.ContextPlugin):
    """This plug-ins displays the comment dialog box per default
    """

    label = "Publish Comment"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        if not context.data.get("comment"):
            context.data["comment"] = ""
