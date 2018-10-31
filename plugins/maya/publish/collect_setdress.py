
import pyblish.api
from reveries.maya.plugins import ls_vessels


class CollectSetDress(pyblish.api.InstancePlugin):
    """Collect avalon sets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect SetDress"
    families = ["reveries.setdress"]

    def process(self, instance):

        set_roots = list()

        for vessel in ls_vessels():
            if vessel in instance:
                self.log.info("Collecting {!r} ..".format(vessel))
                set_roots.append(vessel)

        instance.data["setdressRoots"] = set_roots
