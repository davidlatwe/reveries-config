
import maya.cmds as cmds
import pyblish.api


class CollectTimeline(pyblish.api.ContextPlugin):
    """紀錄時間軸設定值，如 startFrame, endFrame 以及 FPS"""

    """Collect Maya timeline info: start, end frame and fps
    """

    order = pyblish.api.CollectorOrder - 0.4
    hosts = ["maya"]
    label = "時間軸資訊"

    def process(self, context):
        from reveries.maya import lib

        context.data.update(
            {
                "startFrame": cmds.playbackOptions(query=True, minTime=True),
                "endFrame": cmds.playbackOptions(query=True, maxTime=True),
                "fps": lib.current_fps(),
            }
        )
