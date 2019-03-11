
import pyblish.api
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class Disconnect(RepairInstanceAction):

    label = "Disconnect default shaders"


DEFAULT_SHADERS = (
    "initialShadingGroup",
    "initialParticleSE",
)


class ValidateLookNoInitSG(pyblish.api.InstancePlugin):
    """LookDev should not be using default shaders

    Models should not remain using default shaders when publishing
    lookDev.
    For example: lambert1

    """

    label = "No InitShadingGroup"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    families = ["reveries.look"]

    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Disconnect"),
        Disconnect,
    ]

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = list()

        for shape in cmds.ls(instance.data["dagMembers"],
                             type="surfaceShape",
                             noIntermediate=True):
            shaders = cmds.listConnections(shape,
                                           source=False,
                                           destination=True,
                                           type="shadingEngine") or []
            if any(shd in DEFAULT_SHADERS for shd in shaders):
                invalid.append(shape)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error(
                "'%s' has shapes assigned initialShadingGroup:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <No InitShadingGroup> Failed." % instance)

    @classmethod
    def fix_invalid(cls, instance):
        """This will disconnect all connection from default shaders
        """

        from maya import cmds

        invalid = cls.get_invalid(instance)

        cmds.undoInfo(ock=True)
        try:
            for shape in invalid:
                connections = cmds.listConnections(shape,
                                                   type="shadingEngine",
                                                   destination=True,
                                                   connections=True,
                                                   plugs=True) or []

                for src, dst in zip(connections[0::2], connections[1::2]):
                    shader_name = dst.split(".", 1)[0]
                    if shader_name not in DEFAULT_SHADERS:
                        continue

                    cmds.disconnectAttr(src, dst)
        finally:
            cmds.undoInfo(cck=True)
