
import maya.cmds as cmds
import maya.mel as mel
import pyblish.api


class CollectTimeline(pyblish.api.ContextPlugin):
    """Inject the current working scene status into context

    ```
    context.data {
            currentFile:  current working file
            workspaceDir: current working dir
            linearUnits:  maya linear units
            angularUnits: maya angular units
            fps:          maya frame pre second
    }
    ```

    """

    order = pyblish.api.CollectorOrder - 0.249
    hosts = ['maya']
    label = "Scene Timeline"

    def process(self, context):
        context.data.update(
            {
                "startFrame": cmds.playbackOptions(query=True, minTime=True),
                "endFrame": cmds.playbackOptions(query=True, maxTime=True),
                "fps": mel.eval('currentTimeUnitToFPS()'),
            }
        )
