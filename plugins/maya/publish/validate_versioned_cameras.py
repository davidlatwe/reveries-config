
import pyblish.api
from avalon.pipeline import AVALON_CONTAINER_ID
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Not Versioned"


class ValidateVersionedCameras(pyblish.api.InstancePlugin):
    """Camera must be versioned or being published
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Has Versioned Camera"
    families = [
        "reveries.imgseq",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from reveries.maya import lib
        from maya import cmds

        containers = lib.lsAttr("id", AVALON_CONTAINER_ID)

        cameras = set(instance.data["renderCam"])

        has_versioned = set()
        # Is camera being containerized ?
        for cam in cameras:
            transform = cmds.listRelatives(cam, parent=True, fullPath=True)[0]
            for set_ in cmds.listSets(object=transform) or []:
                if set_ in containers:
                    has_versioned.add(cam)
                    break

        not_containerized = cameras - has_versioned
        other_instances = [i for i in instance.context
                           if (not i.data["family"] == "reveries.imgseq" and
                               i.data.get("publish", True))]
        # Is camera being publish ?
        for cam in not_containerized:
            for inst in other_instances:
                if cam in inst:
                    has_versioned.add(cam)
                    break

        return list(cameras - has_versioned)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Camera not versioned.")
