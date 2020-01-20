
import avalon.api


class UpdateNamespace(avalon.api.InventoryAction):
    """Update container imprinted namespace

    Sometimes artist may import loaded subsets from other scene, which
    may prefixing an extra namespace on top of those subsets but the
    namespace attribute in the container did not update hence actions
    like version updating bump into errors.

    This action will lookup subset group node's namespace, and update
    the container if namespace not consistent.

    """
    label = "Update Namespace"
    icon = "wrench"
    color = "#F13A3A"
    order = -100

    @staticmethod
    def is_compatible(container):
        from reveries.maya import lib

        namespace = lib.get_ns(container["subsetGroup"])
        return container["namespace"] != namespace

    def process(self, containers):
        from maya import cmds
        from avalon.tools import sceneinventory
        from reveries.maya import lib

        for container in containers:

            namespace = lib.get_ns(container["subsetGroup"])

            con_node = container["objectName"]
            cmds.setAttr(con_node + ".namespace", namespace, type="string")
            container["namespace"] = namespace

        sceneinventory.app.window.refresh()
