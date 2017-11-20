import pyblish.api


class CollectMayaProfile(pyblish.api.ContextPlugin):
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
    label = "Maya Profile"

    def process(self, context):
        context.data.update(
            {
                "currentFile": self._get_current_file(),
                "workspaceDir": self._get_workspace_dir(),
                "linearUnits": self._get_linear_units(),
                "angularUnits": self._get_units_angle(),
                "fps": self._get_fps()
            }
        )

    @staticmethod
    def _get_current_file():
        import os
        from maya import cmds
        # Collect Current File
        current_file = cmds.file(query=True, sceneName=True)
        return os.path.normpath(current_file)

    @staticmethod
    def _get_workspace_dir():
        import os
        from maya import cmds
        # Collect Current Workspace
        workspace = cmds.workspace(rootDirectory=True, query=True)
        if not workspace:
            # Project has not been set. Files will
            # instead end up next to the working file.
            workspace = cmds.workspace(dir=True, query=True)
        # Maya returns forward-slashes by default
        return os.path.normpath(workspace)

    @staticmethod
    def _get_linear_units():
        from maya import cmds
        return cmds.currentUnit(query=True, linear=True)

    @staticmethod
    def _get_units_angle():
        from maya import cmds
        return cmds.currentUnit(query=True, angle=True)

    @staticmethod
    def _get_fps():
        import maya.mel as mel
        return mel.eval('currentTimeUnitToFPS()')
