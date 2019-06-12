
import os
import json
import shutil
import pyblish.api
import avalon.api
import avalon.io


class ExtractVersionDirectory(pyblish.api.InstancePlugin):
    """Create publish version directory

    * This extractor will lock version by the context data entry
      `"sourceFingerprint"`.

        - The data `"sourceFingerprint"` is a workfile hashing or any other
          feature data that able to identify the workfile change. This should
          be collected via other collector plugin.

        - Before extraction process started, this extractor will create a
          version dir in publish space, and bind that version dir with current
          workfile's fingerprint.

        - If the version dir exists, and the fingerprint matched, the pre-
          existed content in that version dir will be removed.

        - This ensures the version number of the subset will get, after this
          publish session been completed, no matter what happened during
          long extraction time.

    """

    label = "Extract Version Directory"
    order = pyblish.api.ExtractorOrder - 0.4

    META_FILE = ".fingerprint.json"
    MAX_RETRY = 30

    def process(self, instance):
        """Get a version dir which binded to current workfile
        """
        context = instance.context
        project = context.data["projectDoc"]
        root = instance.data.get("reprRoot", avalon.api.registered_root())

        publish_dir_template = project["config"]["template"]["publish"]

        publish_dir_key = {"root": root,
                           "project": avalon.Session["AVALON_PROJECT"],
                           "silo": avalon.Session["AVALON_SILO"],
                           "asset": avalon.Session["AVALON_ASSET"],
                           "subset": instance.data["subset"],
                           "version": None}

        version_dir_template = os.path.dirname(publish_dir_template)

        subset_doc = avalon.io.find_one({
            "type": "subset",
            "parent": context.data["assetDoc"]["_id"],
            "name": instance.data["subset"],
        })

        VERSION_LOCKED = False
        if context.data.get("contractorAccepted"):
            VERSION_LOCKED = True
            self.log.debug("Version Locked.")

        def format_version_dir(version_number):
            """Return a version dir path"""
            self.log.debug("Trying Version: {}".format(version_number))

            publish_dir_key["version"] = version_number
            version_dir = version_dir_template.format(**publish_dir_key)
            # Clean the path
            return os.path.abspath(os.path.normpath(version_dir))

        def write_metadata(version_dir):
            metadata_path = os.path.join(version_dir, self.META_FILE)
            metadata = context.data["sourceFingerprint"]
            metadata["success"] = False

            # Save workfile fingerprint to version dir
            with open(metadata_path, "w") as fp:
                json.dump(metadata, fp, indent=4)

        def is_version_matched(version_dir, strict):
            """Does the fingerprint in this version match with workfile ?"""
            metadata_path = os.path.join(version_dir, self.META_FILE)
            # Load fingerprint from version dir
            with open(metadata_path, "r") as fp:
                metadata = json.load(fp)
                try:
                    success = metadata.pop("success")
                except KeyError:
                    # For backwards compatibility, assuming it succeed
                    success = True

            fingerprint = context.data["sourceFingerprint"]

            same_path = (os.path.normpath(metadata["currentMaking"]) ==
                         os.path.normpath(fingerprint["currentMaking"]))

            if strict:
                same_hash = (metadata["currentHash"] ==
                             fingerprint["currentHash"])

                return same_hash and same_path

            return same_path or not success

        def clean_version_dir(version_dir):
            """Remove all content from the version dir, except fingerprint"""
            self.log.debug("Cleaning version dir.")

            for item in os.listdir(version_dir):
                item_path = os.path.join(version_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    elif os.path.isfile(item_path):
                        os.remove(item_path)
                except Exception as e:
                    self.log.debug(e)

        def get_next_version():
            """Get current subset instance's next version number"""
            if context.data.get("contractorAccepted"):
                # version lock if publish process has been delegated.
                return instance.data["versionNext"]

            version = None
            version_number = 1  # assume there is no version yet, start at 1
            if subset_doc is not None:
                version = avalon.io.find_one({"type": "version",
                                              "parent": subset_doc["_id"]},
                                             {"name": True},
                                             sort=[("name", -1)])
            # if there is a subset there ought to be version
            if version is not None:
                version_number += version["name"]

            return version_number

        # Check
        version = get_next_version()
        tried = 0

        while True:
            if tried > self.MAX_RETRY:
                msg = "Critical Error: Version Dir retry times exceeded."
                self.log.critical(msg)
                raise Exception(msg)

            # Bump version
            version_number = version + tried
            version_dir = format_version_dir(version_number)

            if os.path.isdir(version_dir):
                if is_version_matched(version_dir, VERSION_LOCKED):
                    # This version dir match the current workfile, remove
                    # previous extracted stuff.
                    clean_version_dir(version_dir)
                    write_metadata(version_dir)
                    break

                elif VERSION_LOCKED:
                    # This should not happend.
                    # If the version is locked, the workfile should never
                    # changed.
                    msg = ("Critical Error: Version locked but version dir is "
                           "not available ('sourceFingerprint' not match), "
                           "this is a bug.")
                    self.log.critical(msg)
                    raise Exception(msg)

                else:
                    # Version dir has been created, but the `sourceFingerprint`
                    # not matched because the workfile has changed.
                    # Try next version.
                    pass

            else:
                self.log.debug("Creating version dir.")
                os.makedirs(version_dir)
                write_metadata(version_dir)
                break

            tried += 1

        instance.data["versionNext"] = version_number
        instance.data["versionDir"] = version_dir
        instance.data["publishDirElem"] = (publish_dir_key,
                                           publish_dir_template)

        self.log.debug("Next version: {}".format(version_number))
        self.log.debug("Version dir: {}".format(version_dir))
