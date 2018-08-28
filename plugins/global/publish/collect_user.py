import pyblish.api
import getpass


class CollectUser(pyblish.api.ContextPlugin):
    """Store user name"""

    label = "Collect Current User"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        # (NOTE) Pyblish-QML also provide this info by default with others
        # to the `context.data`, this plugin make sure we are safe without
        # Pyblish-QML's service.
        if not context.data.get("user"):
            context.data["user"] = getpass.getuser()
