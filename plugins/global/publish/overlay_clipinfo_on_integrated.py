
import subprocess
import pyblish.api
from avalon import io


class OverlayClipInfoOnIntegrated(pyblish.api.InstancePlugin):

    label = "Overlay ClipInfo"
    order = pyblish.api.IntegratorOrder + 0.1

    families = [
        "reveries.imgseq.playblast",
    ]

    targets = ["localhost"]

    def process(self, instance):

        context = instance.context
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
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
