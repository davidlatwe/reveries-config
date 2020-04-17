
import pyblish.api
from reveries import plugins


class SelectInvalidOutNodes(plugins.MayaSelectInvalidInstanceAction):

    label = "Invalid Out Nodes"


class ValidateRigOutSetMeshes(pyblish.api.InstancePlugin):
    """Ensure rig OutSet member node type correct

    `OutSet` can only contain models, locators

    """

    label = "Rig OutSet Meshes"
    order = pyblish.api.ValidatorOrder + 0.11
    hosts = ["maya"]

    families = ["reveries.rig"]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalidOutNodes,
    ]

    dependencies = [
        "ValidateRigContents",
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception(
                "'%s' has invalid out nodes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )

    @classmethod
    def get_geometries(cls, instance):
        from maya import cmds

        geometries = set()

        for out_set in instance.data["outSets"]:
            nodes = cmds.sets(out_set, query=True)
            if not nodes:
                cls.log.warning("Rig instance's OutSet %s is empty" % out_set)
                continue

            geometries.update(nodes)

        return list(geometries)

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        if not plugins.depended_plugins_succeed(cls, instance):
            raise Exception("Depended plugin failed. See error log.")

        invalid = list()

        for node in cls.get_geometries(instance):
            if not cmds.nodeType(node) == "transform":
                invalid.append(node)
                continue

            children = cmds.listRelatives(node,
                                          children=True,
                                          fullPath=True) or []

            if not children:
                invalid.append(node)
                continue

            for chd in children:
                if not cmds.ls(chd, type=("mesh", "locator", "constraint")):
                    invalid.append(node)
                    break

        return invalid
