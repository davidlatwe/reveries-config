
import avalon.maya

from reveries.maya.pipeline import put_instance_icon
from reveries import lib


class PointCacheCreator(avalon.maya.Creator):
    """Extract pointcache for deformable objects

    Extract cache for each loaded subset

    """

    label = "PointCache"
    family = "reveries.pointcache"
    icon = "diamond"

    def process(self):
        # Build pipeline render settings

        self.data["exportAlembic"] = True
        self.data["exportGPUCache"] = False
        self.data["exportFBXCache"] = False

        self.data["staticCache"] = False
        self.data["isDummy"] = False

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        # Apply Euler filter to rotations for Alembic
        self.data["eulerFilter"] = True

        return put_instance_icon(super(PointCacheCreator, self).process())
