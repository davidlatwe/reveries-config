
import pyblish.api

from maya import cmds

from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    on = "processed"
    label = "Select Invalided"


class ValidateNoMeshParenting(pyblish.api.InstancePlugin):
    """Validate no mesh parenting under another mesh

    A transform node of a mesh can not be a parent of another transform.

    For example:
        - pCube1
            L pCubeShape1
            L pSphere  <--------- This is not okay.
                L pSphereShape1

    """

    order = pyblish.api.ValidatorOrder
    hosts = ['maya']
    label = "No Mesh Parenting"

    families = [
        "reveries.model",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()
        checked = list()
        for mesh in cmds.ls(instance, long=True, type="mesh"):
            if mesh in checked:
                continue

            parent = cmds.listRelatives(mesh, parent=True, fullPath=True)
            children = cmds.listRelatives(parent, children=True, fullPath=True)

            transforms = cmds.ls(children, type="transform", long=True)
            if transforms:
                invalid += transforms
            checked += children

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            for node in invalid:
                self.log.error("Mesh parenting found: {0}".format(node))
            raise Exception("Mesh parenting found.")
