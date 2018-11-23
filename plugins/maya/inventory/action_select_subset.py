
import avalon.api
from maya import cmds
from reveries.maya.plugins import (
    get_interface_from_container,
    get_group_from_interface,
)


class SelectSubset(avalon.api.InventoryAction):

    label = "Select Subset"
    icon = "cube"
    color = "#d8d8d8"

    def process(self, containers):
        groups = list()

        for container in containers:
            if container.get("loader") == "LookLoader":
                continue

            interface = get_interface_from_container(container["objectName"])
            group = get_group_from_interface(interface)
            groups.append(group)

        cmds.select(groups)
