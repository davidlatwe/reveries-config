
import subprocess
import pyblish.api
from avalon import io


class OverlayClipInfoOnIntegrated(pyblish.api.InstancePlugin):

    label = "Overlay ClipInfo"
    order = pyblish.api.IntegratorOrder + 0.1

    families = [
        "reveries.imgseq.playblast",
    ]

    def process(self, instance):

        context = instance.context
        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        # Check Delegation
        #
        # Contractor completed long-run publish process
        delegated = instance.context.data.get("contractorAccepted")
        # Is delegating long-run publish process
        if instance.data.get("useContractor") and not delegated:
            return

        representation = io.find_one({
            "type": "representation",
            "parent": instance.data["insertedVersionId"],
            "name": "imageSequence"
        })

        id = str(representation["_id"])

        self.log.info("Calling subprocess..")
        popen = subprocess.Popen(["overlay_clipinfo", id],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 shell=True)

        output, _ = popen.communicate()
        self.log.info(output)
