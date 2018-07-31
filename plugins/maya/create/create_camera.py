
import avalon.maya


class CreateCamera(avalon.maya.Creator):
    """Single baked camera"""

    name = "cameraDefault"
    label = "Camera"
    family = "reveries.camera"
    icon = "video-camera"

    def process(self):
        self.data["with_playblast"] = True

        super(CreateCamera, self).process()
