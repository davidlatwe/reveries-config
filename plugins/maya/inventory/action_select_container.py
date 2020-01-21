
import avalon.api


class SelectContainer(avalon.api.InventoryAction):
    """Select container node"""

    label = "Select Container"
    icon = "search"
    color = "#B5D2D7"
    order = 10

    @staticmethod
    def is_compatible(container):
        return True

    def process(self, containers):
        from maya import cmds

        container_nodes = [con["objectName"] for con in containers]
        cmds.select(container_nodes, replace=True, noExpand=True)
