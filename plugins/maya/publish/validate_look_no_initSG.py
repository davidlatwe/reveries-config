
import pyblish.api

from reveries.maya.plugins import MayaSelectInvalidInstanceAction


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
    ]

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = list()

        for shape in cmds.ls(instance.data["dagMembers"],
                             type="surfaceShape",
                             noIntermediate=True):
            shaders = cmds.listConnections(shape, type="shadingEngine") or []
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
