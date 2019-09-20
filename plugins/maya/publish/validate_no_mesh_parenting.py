
import pyblish.api

from maya import cmds

from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

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
        "reveries.rig",
        "reveries.pointcache",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()
        checked = list()

        if "outCache" in instance.data:  # pointcache
            nodes = cmds.listRelatives(instance.data["outCache"],
                                       shapes=True,
                                       noIntermediate=True,
                                       fullPath=True)
            node_type = "deformableShape"
        else:
            nodes = instance[:]
            node_type = "mesh"

        for shape in cmds.ls(nodes, long=True, type=node_type):
            if shape in checked:
                continue

            parent = cmds.listRelatives(shape, parent=True, fullPath=True)
            children = cmds.listRelatives(parent, children=True, fullPath=True)

            for node in cmds.ls(children, type="transform", long=True):
                # (NOTE) constraint node is allowed.
                if cmds.listRelatives(node,
                                      allDescendents=True,
                                      type="shape"):
                    invalid.append(node)

            checked += children

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            max_prompt = 10
            total = len(invalid)

            for node in invalid[:max_prompt]:
                self.log.error("Mesh parenting found: {0}".format(node))

            if total > max_prompt:
                self.log.warning("Error message truncated. "
                                 "Invalid count: %d" % total)

            raise Exception("Mesh parenting found.")
