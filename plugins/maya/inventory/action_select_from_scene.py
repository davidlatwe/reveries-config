
import avalon.api
import avalon.maya
from maya import cmds


class SelectFromScene(avalon.api.InventoryAction):

    label = "Select From Scene"
    icon = "hand-o-up"
    color = "#66aa66"
    order = 100

    @staticmethod
    def is_compatible(container):
        return True

    def process(self, containers):

        containers = avalon.maya.ls()
        container_names = set(c["objectName"] for c in containers)

        selected = cmds.ls(sl=True)
        selected_items = set()

        for node in selected:
            if node in container_names:
                selected_items.add(node)
                continue

            objsets = cmds.listSets(object=node) or []
            for objset in objsets:
                if objset in container_names:
                    selected_items.add(objset)
                    break

        return selected_items
