
import pyblish.api
from reveries import plugins


class SelectInvalidInMesh(plugins.MayaSelectInvalidInstanceAction):

    label = "Invalid InMesh"


class FixInputMesh(plugins.RepairInstanceAction):

    label = "Fix InMesh"


class ValidateRigNoPlaceholderInput(pyblish.api.InstancePlugin):
    """Validate no mesh input from reference placeholder

    If someone update model aggressively and reckless, some
    of the rig deformed mesh's input mesh may missing from
    reference due to name change.

    In this situation, the input mesh will be connected from
    reference placeholder.

    Although it may seems normal in scene, but if you import
    the referenced model, save the file and re-open it, you
    will find that mesh has no vertices at all.

    Current fix:
        If there's another referenced intermediate mesh, change
        to use it's `worldMesh` over placeholder.

    """

    label = "No Placeholder Input Mesh"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.rig"]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalidInMesh,
        pyblish.api.Category("Fix It"),
        FixInputMesh,
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Found mesh input from reference placeholder.")

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds
        from reveries.maya import lib

        invalid = dict()

        mesh_nodes = cmds.ls(instance,
                             type="mesh",
                             noIntermediate=True,
                             long=True)
        for mesh in mesh_nodes:
            attr = mesh + ".inMesh"
            history = cmds.listHistory(attr, pruneDagObjects=True)
            reference = lib.get_reference_nodes(history)
            if reference:
                reference = reference[0]
                transform = cmds.listRelatives(mesh,
                                               parent=True,
                                               fullPath=True)[0]
                # Get the first (most upstream) node that input mesh was
                # reference placeholder. That node should be at the index
                # before reference node in history node list.
                input = history[history.index(reference) - 1]
                invalid[transform] = (mesh, reference, input)

        return invalid

    @classmethod
    def fix_invalid(cls, instance):
        from maya import cmds

        invalid = cls.get_invalid(instance)
        for transform, (deformed, reference, input) in invalid.items():
            origin = None

            for mesh in cmds.listRelatives(transform,
                                           shapes=True,
                                           fullPath=True):
                if not cmds.getAttr(mesh + ".intermediateObject"):
                    continue
                if not cmds.ls(mesh, referencedNodes=True):
                    continue

                origin = mesh
                break

            else:
                cls.log.warning("Could not fix %s." % transform)
                continue

            # Replace placeholder with newly referenced origin mesh
            conns = cmds.listConnections(input,
                                         source=True,
                                         destination=False,
                                         plugs=True,
                                         connections=True)
            conns = iter(conns)
            for dst, src in zip(conns, conns):
                if src.startswith(reference + ".placeHolderList"):
                    cmds.connectAttr(origin + ".worldMesh", dst, force=True)
                    break
