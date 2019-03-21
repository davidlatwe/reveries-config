
import os
import json
import pyblish.api


class PublishSucceed(pyblish.api.ContextPlugin):

    label = "Publish Succeed"
    order = pyblish.api.IntegratorOrder + 0.499999

    META_FILE = ".fingerprint.json"

    def process(self, context):
        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            version_dir = instance.data["versionDir"]
            metadata_path = os.path.join(version_dir, self.META_FILE)

            with open(metadata_path, "r") as fp:
                metadata = json.load(fp)

            metadata["success"] = True

            with open(metadata_path, "w") as fp:
                    json.dump(metadata, fp, indent=4)
