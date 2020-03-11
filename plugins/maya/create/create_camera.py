
import avalon.maya
from reveries.maya.pipeline import put_instance_icon
from reveries import lib


class CameraCreator(avalon.maya.Creator):
    """Single baked camera"""

    label = "Camera"
    family = "reveries.camera"
    icon = "video-camera"

    def process(self):
        self.data["bakeStep"] = 1.0
        # Apply Euler filter to rotations for Alembic
        self.data["eulerFilter"] = False

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        return put_instance_icon(super(CameraCreator, self).process())
