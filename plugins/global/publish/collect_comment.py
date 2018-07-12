import pyblish.api

_COMMENT = ""


class CollectComment(pyblish.api.ContextPlugin):
    """This plug-ins displays the comment dialog box per default

    ```
    context.data {
            comment: user comment,
    }
    ```

    """

    label = "Publish Comment"
    order = pyblish.api.CollectorOrder - 0.45

    def process(self, context):
        global _COMMENT
        context.data["comment"] = _COMMENT


def fetch_comment(comment):
    global _COMMENT
    _COMMENT = comment


pyblish.api.register_callback("commented", fetch_comment)
