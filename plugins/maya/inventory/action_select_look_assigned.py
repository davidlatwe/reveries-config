
import avalon.api
import avalon.maya
from maya import cmds

from reveries.maya.capsule import maintained_selection


class SelectAssigned(avalon.api.InventoryAction):

    label = "Look Assigned"
    icon = "eye"
    color = "#d8d8d8"

    @staticmethod
    def is_compatible(container):
        return container.get("loader") == "LookLoader"

    def process(self, containers):

        shaders = set()
        for container in containers:
            if not container.get("loader") == "LookLoader":
                continue

            # Select assigned
            members = cmds.sets(container["objectName"], query=True)
            shaders.update(cmds.ls(members, type="shadingEngine"))

        with maintained_selection():
            cmds.select(list(shaders), replace=True)

            # Parse selected
            containers = avalon.maya.ls()
            container_names = set(c["objectName"] for c in containers)

            selected_items = set()
            for node in cmds.ls(sl=True, objectsOnly=True):
                objsets = cmds.listSets(object=node) or []
                for objset in objsets:
                    if objset in container_names:
                        selected_items.add(objset)
                        break

        return selected_items
