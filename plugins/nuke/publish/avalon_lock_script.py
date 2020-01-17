
import os
import pyblish.api
import nuke
from avalon.nuke import workio
from reveries.nuke import pipeline


class AvalonLockScript(pyblish.api.ContextPlugin):
    """Forbid saving any work file modification once entering extraction

    Save script into a folder called "_published" under work area, any script
    that saved in that folder can not be overwritten.

    """

    label = "Lock and Save Script"
    order = pyblish.api.ExtractorOrder - 0.499
    hosts = ["nuke"]

    def process(self, context):

        assert any(inst.data.get("publish", True) for inst in context), (
            "No instance been published, aborting.")

        if pipeline.is_locked():
            return

        # Rename scene file (Save As)
        script = os.path.basename(workio.current_file())
        workspace = workio.work_root()

        basename, ext = os.path.splitext(script)

        publishing_dir = workspace + "/_published/"
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

        context.data["originMaking"] = context.data["currentMaking"]
        context.data["currentMaking"] = publishing

        # Lock & Save
        nuke.scriptSaveAs(publishing)
