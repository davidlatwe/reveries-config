import pyblish.api
import getpass


class CollectUser(pyblish.api.ContextPlugin):
    """Store user name"""

    label = "Collect Current User"
    order = pyblish.api.CollectorOrder

    def process(self, context):
        # (NOTE) Pyblish-QML also provide this info by default with others
        # to the `context.data`, this plugin make sure we are safe without
        # Pyblish-QML's service.
        context.data["user"] = getpass.getuser()
