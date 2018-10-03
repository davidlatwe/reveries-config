
import pyblish.api
import avalon.api


class ValidateAssetSession(pyblish.api.InstancePlugin):

    label = "Asset Session"
    order = pyblish.api.ValidatorOrder - 0.45

    def process(self, instance):
        asset = instance.data["asset"]
        task_asset = avalon.api.Session["AVALON_ASSET"]

        if not asset == task_asset:
            msg = ("Instance {name!r} is not belong to Asset {asset!r}. "
                   "Please check Context Manager."
                   "".format(name=instance.data["name"],
                             asset=task_asset))
            self.log.error(msg)
            raise AssertionError(msg)
