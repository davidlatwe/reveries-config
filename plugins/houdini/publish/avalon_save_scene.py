
import os
import shutil
import pyblish.api


class AvalonSaveScene(pyblish.api.ContextPlugin):
    """Save current scene and copy a publish backup
    """

    label = "Save Scene"
    order = pyblish.api.ExtractorOrder - 0.499
    hosts = ["houdini"]

    def process(self, context):
        import hou

        hou.hipFile.save()
        current_scene = context.data["currentMaking"]
        scene_dir, scene_file = os.path.split(current_scene)

        basename, ext = os.path.splitext(scene_file)

        publishing_dir = scene_dir + "/_published/"
        publishing_file = basename + ".published%s" + ext
        publishing = None

        if not os.path.isdir(publishing_dir):
            os.makedirs(publishing_dir)

        exists = True
        suffix = ""
        index = 0
        while exists:
            publishing = publishing_dir + publishing_file % suffix
            failed = publishing_dir + "__failed." + publishing_file % suffix
            exists = os.path.isfile(publishing) or os.path.isfile(failed)
            index += 1
            suffix = ".%02d" % index

        context.data["originMaking"] = current_scene
        context.data["currentMaking"] = publishing

        # Copy scene file
        shutil.copy2(current_scene, publishing)
