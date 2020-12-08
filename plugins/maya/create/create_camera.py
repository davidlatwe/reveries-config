
import avalon.maya
from avalon import io, api
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
        self.data["eulerFilter"] = True

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        self.data["overSessionAsset"] = False

        # For usd setting
        self.data["publishUSD"] = False
        project = io.find_one({"name": api.Session["AVALON_PROJECT"],
                               "type": "project"})

        if project.get('usd_pipeline', False):
            self.data["publishUSD"] = True

        return put_instance_icon(super(CameraCreator, self).process())
