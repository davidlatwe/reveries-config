
import pyblish.api
import avalon.api


class ValidateAssetSession(pyblish.api.InstancePlugin):
    """Only the asset which assigned to this task can be published

    The asset to be published should be the same as the asset of the
    task (current workspace).
    For example, if you are in the task of the asset *Boy*, you can
    not publish asset *Girl* in current session.

    """

    label = "Asset Session"
    order = pyblish.api.ValidatorOrder - 0.45

    def process(self, instance):
        asset = instance.data["asset"]
        task_asset = avalon.api.Session["AVALON_ASSET"]

        if not asset == task_asset:
            msg = ("Instance {name!r} has been set to be as part of "
                   "Asset: {asset!r}, but the current publish session "
                   "is Asset: {task_asset!r}. "
                   "Please check Context Manager."
                   "".format(name=str(instance.data["name"]),
                             asset=str(asset),
                             task_asset=str(task_asset)))
            self.log.error(msg)
            raise AssertionError(msg)
