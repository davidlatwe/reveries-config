import pyblish.api
from maya import cmds


class SelectInvalid(pyblish.api.Action):
    label = "Select Invalid"
    on = "processed"
    icon = "hand-o-up"

    def process(self, context, plugin):
        cmds.select(plugin.invalid)


class ValidateNoSmoothPreview(pyblish.api.InstancePlugin):
    """Emit Warning If There are any mesh has smooth preview"""

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.45
    hosts = ['maya']
    label = "No Smooth Preview"
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    invalid = []

    def process(self, instance):
        """Process all the nodes in the instance"""

        for mesh in cmds.ls(instance, type="mesh", long=True):
            if cmds.getAttr("{0}.displaySmoothMesh".format(mesh)):
                self.invalid.append(mesh)

        if self.invalid:
            self.log.warning("Smooth Preview found: {0}".format(self.invalid))
            self.log.warning("<No Smooth Preview> Warned.")
        else:
            self.log.info("%s <No Smooth Preview> Passed." % instance)
