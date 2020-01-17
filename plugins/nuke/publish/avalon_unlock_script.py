
import os
import pyblish.api
import nuke
from reveries import lib


class AvalonUnlockScript(pyblish.api.ContextPlugin):
    """Unlock Nuke Script
    """

    label = "Unlock And Save Script"
    order = pyblish.api.IntegratorOrder + 0.499
    hosts = ["nuke"]

    def process(self, context):

        if lib.in_remote():
            return

        fname = context.data["originMaking"]

        if all(result["success"] for result in context.data["results"]):

            self.log.info("Publish succeed, save script back to workfile.")
            nuke.scriptSaveAs(fname, overwrite=True)
            modified = False

        else:
            # Mark failed if error raised during extraction or integration
            publishing = context.data["currentMaking"]
            script_dir, file_name = os.path.split(publishing)
            file_name = "__failed." + file_name
            modified = True

            os.rename(publishing, script_dir + "/" + file_name)

        nuke.Root()["name"].setValue(fname)
        nuke.Root()["project_directory"].setValue(os.path.dirname(fname))
        nuke.Root().setModified(modified)
