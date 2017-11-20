import pyblish.api
from maya import cmds
from reveries.maya import action


class ValidateMeshNoNegativeScale(pyblish.api.Validator):
    """Ensure that meshes don't have a negative scale.

    Using negatively scaled proxies in a VRayMesh results in inverted
    normals. As such we want to avoid this.

    We also avoid this on the rig or model because these are often the
    previous steps for those that are cached to proxies so we can catch this
    issue early.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    hosts = ['maya']
    label = 'Mesh No Negative Scale'
    actions = [action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):
        meshes = cmds.ls(instance,
                         type='mesh',
                         long=True,
                         noIntermediate=True)

        invalid = []
        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            scale = cmds.getAttr("{0}.scale".format(transform))[0]

            if any(x < 0 for x in scale):
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Meshes found with negative scale:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh No Negative Scale> Failed." % instance)

        self.log.info("%s <Mesh No Negative Scale> Passed." % instance)
