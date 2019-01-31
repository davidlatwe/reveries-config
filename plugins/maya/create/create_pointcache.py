
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class PointCacheCreator(avalon.maya.Creator):
    """Any cacheable object"""

    label = "PointCache"
    family = "reveries.pointcache"
    icon = "diamond"

    def process(self):
        self.data["extractType"] = [
            "Alembic",
            "GPUCache",
            "FBXCache",
        ]

        self.data["staticCache"] = False

        # Build pipeline render settings

        project = avalon.io.find_one({"type": "project"},
                                     projection={"data": True})
        deadline = project["data"]["deadline"]["maya"]

        priority = deadline["priorities"]["pointcache"]

        self.data["deadlineEnable"] = False
        self.data["deadlinePriority"] = priority
        self.data["deadlinePool"] = ["none"] + deadline["pool"]
        self.data["deadlineGroup"] = deadline["group"]

        return put_instance_icon(super(PointCacheCreator, self).process())
