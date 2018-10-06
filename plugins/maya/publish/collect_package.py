
import pyblish.api
from reveries.maya.plugins import read_interface_to_package


class CollectPackage(pyblish.api.InstancePlugin):
    """Collect avalon containers data
    """

    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["maya"]
    label = "Collect Package"
    families = ["reveries.setdress"]

    def process(self, instance):

        package = dict()

        for interface in instance.data["interfaces"]:
            _id, data = read_interface_to_package(interface)

            self.log.info("Collecting {!r} ..".format(interface))

            package[_id] = package.get(_id, data)
            package[_id]["count"] = package[_id].get("count", 0) + 1

        # For debug
        for _id, data in package.items():
            self.log.debug("ID: {}".format(_id))
            for k, v in data.items():
                self.log.debug("{0}: {1}".format(k, v))

        instance.data["packageData"] = package
