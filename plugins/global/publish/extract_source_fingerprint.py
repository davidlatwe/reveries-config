
import os
import pyblish.api

from reveries.utils import AssetHasher


class ExtractSourceFingerprint(pyblish.api.ContextPlugin):

    label = "Extract Fingerprint"
    order = pyblish.api.ExtractorOrder - 0.4

    def process(self, context):

        current_making = context.data["currentMaking"]
        hasher = AssetHasher()

        if os.path.isfile(current_making):
            hasher.add_file(current_making)

        if os.path.isdir(current_making):
            hasher.add_dir(current_making)

        context.data["sourceFingerprint"] = {
            "currentMaking": current_making,
            "currentHash": hasher.digest(),
        }
