
import pyblish.api
from avalon.pipeline import AVALON_CONTAINER_ID
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Not Versioned"


class ValidateCameraVersioned(pyblish.api.InstancePlugin):
    """Camera must be versioned or being published
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Is Versioned Camera"
    families = [
        "reveries.renderlayer",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    camera_family = "reveries.camera"

    @classmethod
    def get_invalid(cls, instance):
        from reveries.maya import lib
        from maya import cmds

        invalid = list()
        camera = instance.data["camera"]

        # Is camera being containerized ?
        containers = lib.lsAttr("id", AVALON_CONTAINER_ID)
        transform = cmds.listRelatives(camera, parent=True, fullPath=True)[0]
        for set_ in cmds.listSets(object=transform) or []:
            if set_ in containers:
                break
        else:
            # Is camera being publish ?
            camera_instances = [i for i in instance.context
                                if (i.data["family"] == cls.camera_family and
                                    i.data.get("publish", True))]
            if not any(camera in inst for inst in camera_instances):
                invalid.append(camera)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Camera not versioned.")
