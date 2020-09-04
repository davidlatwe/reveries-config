
import avalon.maya
from reveries.maya.pipeline import put_instance_icon


class AtomsCrowdCreator(avalon.maya.Creator):
    """Atoms Crowd"""

    label = "Atoms Crowd"
    family = "reveries.atomscrowd"
    icon = "building"

    def process(self):
        import maya.cmds as cmds

        scene_start = cmds.playbackOptions(query=True, minTime=True)
        scene_end = cmds.playbackOptions(query=True, maxTime=True)

        self.data["useCustomRange"] = True
        self.data["startFrame"] = scene_start
        self.data["endFrame"] = scene_end

        return put_instance_icon(super(AtomsCrowdCreator, self).process())
