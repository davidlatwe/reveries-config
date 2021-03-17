
import avalon.maya
from avalon import io, api

from reveries.maya.pipeline import put_instance_icon
from reveries import lib


class SkeletonCacheCreator(avalon.maya.Creator):
    """Extract pointcache for deformable objects

    Extract cache for each loaded subset

    """

    label = "SkeletonCache"
    family = "reveries.skeletoncache"
    icon = "child"

    def process(self):
        self.data["isDummy"] = False

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        return put_instance_icon(super(SkeletonCacheCreator, self).process())
