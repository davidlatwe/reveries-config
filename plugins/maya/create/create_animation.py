
from maya import cmds
import avalon.maya
import avalon.io

from reveries.maya.pipeline import put_instance_icon


class AnimationCreator(avalon.maya.Creator):
    """Any character or prop animation"""

    label = "Animation"
    family = "reveries.animation"
    icon = "male"

    def process(self):
        # Build pipeline render settings

        project = avalon.io.find_one({"type": "project"},
                                     projection={"data": True})
        pipeline = project["data"]["pipeline"]["maya"]
        deadline = project["data"]["deadline"]["maya"]

        priority = deadline["priorities"]["pointcache"]

        self.data["extractType"] = pipeline.get("pointcache", "Alembic")

        self.data["deadlineEnable"] = False
        self.data["deadlinePriority"] = priority
        self.data["deadlinePool"] = ["none"] + deadline["pool"]
        self.data["deadlineGroup"] = deadline["group"]

        instance = super(AnimationCreator, self).process()
        cmds.setAttr(instance + ".extractType", lock=True)

        return put_instance_icon(instance)
