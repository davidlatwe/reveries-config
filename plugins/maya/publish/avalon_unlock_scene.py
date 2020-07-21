
import os
import pyblish.api


class AvalonUnlockScene(pyblish.api.ContextPlugin):
    """Unlock Maya scene
    """

    label = "Unlock And Save Scene"
    order = pyblish.api.IntegratorOrder + 0.3
    hosts = ["maya"]

    def process(self, context):
        from maya import cmds
        from avalon import maya
        from reveries.maya import capsule

        if context.data.get("_autoPublishingSkipUnlock"):
            self.log.info("Auto publishing, skip unlock.")
            return

        maya.unlock()

        with capsule.maintained_selection():
            cmds.file(rename=context.data["originMaking"])
            # Changing selection to update window title for
            # displaying new file name
            cmds.select("defaultLightSet")

        if all(result["success"] for result in context.data["results"]):

            self.log.info("Publish succeed, save scene back to workfile.")
            cmds.file(save=True, force=True)

        else:
            # Mark failed if error raised during extraction or integration
            publishing = context.data["currentMaking"]
            scene_dir, file_name = os.path.split(publishing)
            file_name = "__failed." + file_name

            os.rename(publishing, scene_dir + "/" + file_name)
