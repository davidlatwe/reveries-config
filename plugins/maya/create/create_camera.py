
import avalon.maya
from maya import cmds


class CreateCamera(avalon.maya.Creator):
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

        container = super(CreateCamera, self).process()
        cmds.setAttr(container + ".publish_contractor", lock=True)
