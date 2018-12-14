
import avalon.maya
from maya import cmds

from reveries.maya.pipeline import put_instance_icon


class CameraCreator(avalon.maya.Creator):
    """Single baked camera"""

    name = "cameraDefault"
    label = "Camera"
    family = "reveries.camera"
    icon = "video-camera"

    contractor = "deadline.maya.script"

    def process(self):
        self.data["capture_png"] = True

        self.data["publish_contractor"] = self.contractor
        self.data["use_contractor"] = True

        instance = super(CameraCreator, self).process()
        cmds.setAttr(instance + ".publish_contractor", lock=True)

        return put_instance_icon(instance)
