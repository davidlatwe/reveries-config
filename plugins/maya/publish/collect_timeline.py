
import maya.cmds as cmds
import maya.mel as mel
import pyblish.api


class CollectTimeline(pyblish.api.ContextPlugin):
    """Collect Maya timeline info: start, end frame and fps
    """

    order = pyblish.api.CollectorOrder - 0.4
    hosts = ["maya"]
    label = "Scene Timeline"

    def process(self, context):
        context.data.update(
            {
                "startFrame": cmds.playbackOptions(query=True, minTime=True),
                "endFrame": cmds.playbackOptions(query=True, maxTime=True),
                "fps": mel.eval('currentTimeUnitToFPS()'),
            }
        )
