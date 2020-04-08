
import os
import pyblish.api


class AvalonFailScene(pyblish.api.ContextPlugin):
    """Rename publish backup scene if any error raised during publish
    """

    label = "Fail Scene On Error"
    order = pyblish.api.IntegratorOrder + 0.499
    hosts = ["houdini"]

    def process(self, context):

        if all(result["success"] for result in context.data["results"]):
            # Publish succeed
            return

        else:
            # Mark failed if error raised during extraction or integration
            publishing = context.data["currentMaking"]
            scene_dir, file_name = os.path.split(publishing)
            file_name = "__failed." + file_name

            os.rename(publishing, scene_dir + "/" + file_name)
