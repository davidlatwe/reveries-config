import pyblish.api
from reveries.maya import action
from maya import cmds


class ValidateNoSmoothPreview(pyblish.api.InstancePlugin):
    """Emit Warning If There are any mesh has smooth preview"""

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.45
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = "No Smooth Preview"

    @staticmethod
    def get_invalid(instance):
        invalid = list()
        for mesh in instance.data['meshes']:
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
