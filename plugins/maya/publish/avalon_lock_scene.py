
import os
import pyblish.api
from maya import cmds
from avalon import maya


class AvalonLockScene(pyblish.api.ContextPlugin):
    """Forbid saving any work file modification once entering extraction

    A node is placed within the scene called "lock" where the name of
    the file as it exists currently is imprinted. If an attempt is made
    to publish this file where the name of the file and that in the lock
    is a match, publishing fails.

    Scene will be saved.

    """

    label = "Lock and Save Scene"
    order = pyblish.api.ExtractorOrder - 0.499
    hosts = ["maya"]

    def process(self, context):

        assert any(inst.data.get("publish", True) for inst in context), (
            "No instance been published, aborting.")

        if maya.is_locked():
            return

        # Switch to masterLayer before save
        cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")

        # Rename scene file (Save As)
        scene_file = os.path.basename(cmds.file(query=True, sceneName=True))
        scene_dir = (cmds.workspace(query=True, rootDirectory=True) +
                     cmds.workspace(fileRuleEntry="scene"))

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

        context.data["originMaking"] = context.data["currentMaking"]
        context.data["currentMaking"] = publishing

        cmds.file(rename=publishing)

        # Lock & Save
        maya.lock()
        with maya.lock_ignored():
            cmds.file(save=True, force=True)
