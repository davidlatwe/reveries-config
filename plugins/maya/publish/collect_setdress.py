
import pyblish.api
from reveries.maya.plugins import parse_group_from_interface


class CollectSetDress(pyblish.api.InstancePlugin):
    """Collect avalon sets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect SetDress"
    families = ["reveries.setdress"]

    def process(self, instance):

        all_roots = dict()

        for interface in instance.data["interfaces"]:
            try:
                root = parse_group_from_interface(interface)
            except RuntimeError:
                # No group found
                root = None

            all_roots[str(interface)] = root

        for intf, root in all_roots.items():
            self.log.debug(intf)
            self.log.debug(">>  " + root)

        instance.data["setdressRoots"] = all_roots
