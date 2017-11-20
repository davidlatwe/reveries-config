import pyblish.api


class CollectShellProfile(pyblish.api.ContextPlugin):
    """Inject the current working scene status into context

    ```
    context.data {
            currentFile:  current working file
            workspaceDir: current working dir
    }
    ```

    """

    order = pyblish.api.CollectorOrder - 0.4
    hosts = ["shell"]
    label = "Shell Profile"

    def process(self, context):
        context.data.update(
            {
                "currentFile": self._get_current_file(),
                "workspaceDir": self._get_workspace_dir()
            }
        )

    @staticmethod
    def _get_current_file():
        import os
        return os.path.join(os.getcwd(), "<shell>")

    @staticmethod
    def _get_workspace_dir():
        import os
        return os.getcwd()
