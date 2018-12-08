
import pyblish.api
import maya.cmds as cmds
from reveries.maya.plugins import (
    get_interface_from_container,
    get_group_from_interface,
    parse_interface,
)


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
        inst_data = list()

        self.sub_containers = instance.context.data["SubContainers"]
        root_containers = instance.context.data["RootContainers"].values()

        for container in root_containers:

            interface = get_interface_from_container(container["objectName"])
            interface = parse_interface(interface)
            vessel = get_group_from_interface(interface["objectName"])

            if vessel in instance:
                self.log.info("Collecting {!r} ..".format(vessel))

                set_groups.append(vessel)

                # The namespace stored in interface was absolute name,
                # need to save as relative name.
                # e.g. ":awesome" -> "awesome"
                namespace = interface["namespace"][1:]

                root = cmds.listRelatives(vessel, parent=True, fullPath=True)
                root = (root or [None])[0]
                matrix = cmds.xform(vessel,
                                    query=True,
                                    matrix=True,
                                    objectSpace=True)

                data = {
                    "namespace": namespace,
                    "containerId": interface["containerId"],
                    "root": root,
                    "matrix": matrix,
                    "loader": interface["loader"],
                    "representation": interface["representation"],
                    "representationId": interface["representationId"],

                    # Member dict
                    "hierarchyRepresentation": self.walk_members(container),

                    # For extraction use, will be removed
                    "container": container,
                }

                inst_data.append(data)

                if root not in set_roots:
                    set_roots.append(root)

        instance.data["setdressRoots"] = set_roots
        instance.data["setdressGroups"] = set_groups
        instance.data["setMembersData"] = inst_data

    def walk_members(self, container):
        child_rp = dict()

        for child in container["children"]:

            child_container = self.sub_containers[child]
            child_interface = get_interface_from_container(child)
            child_interface = parse_interface(child_interface)

            child_container_id = child_interface["containerId"]

            child_representation_id = child_container["representation"]
            child_namespace = child_container["namespace"].rsplit(":", 1)[-1]
            child_ident = child_representation_id + "|" + child_namespace

            child_rp[child_container_id] = {
                child_ident: self.walk_members(child_container)
            }

        return child_rp
