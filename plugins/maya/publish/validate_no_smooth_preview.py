
import pyblish.api

from maya import cmds

from reveries.maya.plugins import MayaSelectInvalidAction


class SelectInvalid(MayaSelectInvalidAction):

    on = "processed"
    label = "Select Smooth Preview"


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

    @staticmethod
    def get_invalid(instance):

        invalid = list()

        for mesh in cmds.ls(instance, type="mesh", long=True):
            if cmds.getAttr("{0}.displaySmoothMesh".format(mesh)):
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.warning("Smooth Preview found: {0}".format(invalid))
            self.log.warning("<No Smooth Preview> Warned.")
        else:
            self.log.info("%s <No Smooth Preview> Passed." % instance)
