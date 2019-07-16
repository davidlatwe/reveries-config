
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class PointCacheCreator(avalon.maya.Creator):
    """Extract pointcache for deformable objects

    Extract cache for each loaded subset

    """

    label = "PointCache"
    family = "reveries.pointcache"
    icon = "diamond"

    def process(self):
        # Build pipeline render settings

        project = avalon.io.find_one({"type": "project"},
                                     projection={"data": True})
        pipeline = project["data"]["pipeline"]["maya"]
        deadline = project["data"]["deadline"]["maya"]

        cache_type = pipeline["pointcache"]
        priority = deadline["priorities"]["pointcache"]

        self.data["extractType"] = cache_type[:]

        self.data["staticCache"] = False

        self.data["deadlineEnable"] = False
        self.data["deadlinePriority"] = priority
        self.data["deadlinePool"] = ["none"] + deadline["pool"]
        self.data["deadlineGroup"] = deadline["group"]

        # Apply Euler filter to rotations for Alembic
        self.data["eulerFilter"] = False

        return put_instance_icon(super(PointCacheCreator, self).process())
