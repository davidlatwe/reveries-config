
import os
import shutil
import pyblish.api


class AvalonSourceInDeadline(pyblish.api.ContextPlugin):
    """Save current scene and copy a publish backup
    """

    label = "Use Source In Deadline"
    order = pyblish.api.ExtractorOrder - 0.498
    hosts = ["houdini"]

    targets = ["deadline"]

    families = [
        "reveries.fx.layer_prim",
    ]

    def process(self, context):
        current_scene = context.data["originMaking"]

        _, scene_file = os.path.split(context.data["currentMaking"])
        scene_dir, _ = os.path.split(current_scene)
        
        publish_file_name = ".publish_{}".format(scene_file)
        publishing = os.path.join(
            scene_dir, publish_file_name).replace("\\", "/")

        #
        context.data["currentMaking"] = publishing

        # Copy scene file
        shutil.copy2(current_scene, publishing)
