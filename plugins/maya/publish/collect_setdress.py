
import pyblish.api
from reveries.maya.plugins import ls_interfaces, get_group_from_interface


class CollectSetDress(pyblish.api.InstancePlugin):
    """Collect avalon sets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect SetDress"
    families = ["reveries.setdress"]

    def process(self, instance):

        set_roots = list()
        pkg_data = dict()

        for interface in ls_interfaces():
            vessel = get_group_from_interface(interface["objectName"])

            if vessel in instance:
                self.log.info("Collecting {!r} ..".format(vessel))

                set_roots.append(vessel)

                repr_id = interface["representation_id"]
                if repr_id not in pkg_data:
                    pkg_data[repr_id] = list()
                pkg_data[repr_id].append(interface)

        instance.data["setdressRoots"] = set_roots
        instance.data["packageData"] = pkg_data
