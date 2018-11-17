
import pyblish.api
from avalon.pipeline import AVALON_CONTAINER_ID
from maya import cmds
from reveries.maya import lib


class ValidateLookSingleSubset(pyblish.api.InstancePlugin):
    """Ensure one and only one model subset in look instance

    One look subset must pair to one and only one model subset, can not
    publish look on multiple subsets.

    """

    label = "Look On Single Subset"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.look"]

    def process(self, instance):
        paired = list()
        containers = lib.lsAttr("id", AVALON_CONTAINER_ID)

        meshes = cmds.ls(instance.data["dag_members"],
                         visible=True,
                         noIntermediate=True,
                         type="mesh")

        for mesh in meshes:
            for set_ in cmds.listSets(object=mesh):
                if set_ in containers and set_ not in paired:
                    paired.append(set_)

        if not len(paired):
            raise Exception("No model subset found.")

        if len(paired) > 1:
            raise Exception("One look instance can only pair to "
                            "one model subset.")
