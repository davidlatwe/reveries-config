
import pyblish.api
from maya import cmds


class SelectInvalid(pyblish.api.Action):
    label = "Select Invalid"
    on = "failed"
    icon = "hand-o-up"

    def process(self, context, plugin):
        cmds.select(plugin.invalid)


class ValidateLookNoInitSG(pyblish.api.InstancePlugin):

    label = "No InitShadingGroup"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    families = ["reveries.look"]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    DEFAULT_SHADERS = (
        "initialShadingGroup",
        "initialParticleSE",
    )

    invalid = []

    def process(self, instance):

        for shape in cmds.ls(instance, type="mesh", noIntermediate=True):
            shaders = cmds.listConnections(shape, type="shadingEngine") or []
            if any(shd in self.DEFAULT_SHADERS for shd in shaders):
                self.invalid.append(shape)

        if self.invalid:
            self.log.error(
                "'%s' has shapes assigned initialShadingGroup:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in self.invalid))
            )
            raise Exception("%s <No InitShadingGroup> Failed." % instance)
