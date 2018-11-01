
import pyblish.api
import maya.cmds as cmds
from reveries.maya.plugins import ls_interfaces, get_group_from_interface


class CollectSetDress(pyblish.api.InstancePlugin):
    """Collect avalon sets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect SetDress"
    families = ["reveries.setdress"]

    def process(self, instance):

        set_roots = list()   # subsets' reference group node's parent node
        set_groups = list()  # subsets' reference group node
        inst_data = dict()

        for interface in ls_interfaces():
            vessel = get_group_from_interface(interface["objectName"])

            if vessel in instance:
                self.log.info("Collecting {!r} ..".format(vessel))

                set_groups.append(vessel)

                repr_id = interface["representation_id"]
                if repr_id not in inst_data:
                    inst_data[repr_id] = {
                        "loader": interface["loader"],
                        "instances": list(),
                    }

                root = cmds.listRelatives(vessel, parent=True, fullPath=True)
                root = (root or [None])[0]
                matrix = cmds.xform(vessel,
                                    query=True,
                                    matrix=True,
                                    objectSpace=True)

                # The namespace stored in interface was absolute name,
                # need to save as relative name.
                # e.g. ":awesome" -> "awesome"
                namespace = interface["namespace"][1:]

                data = {
                    "namespace": namespace,
                    "root": root,
                    "matrix": matrix,
                }

                if root not in set_roots:
                    set_roots.append(root)
                inst_data[repr_id]["instances"].append(data)

        instance.data["setdressRoots"] = set_roots
        instance.data["setdressGroups"] = set_groups
        instance.data["instancesData"] = inst_data
