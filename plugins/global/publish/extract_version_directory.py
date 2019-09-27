
import os
import json
import shutil
import logging
import pyblish.api
import avalon.api
import avalon.io


class VersionManager(object):

    META_FILE = ".publish.meta.json"

    def __init__(self, instance):
        context = instance.context

        project = context.data["projectDoc"]
        root = instance.data.get("reprRoot", avalon.api.registered_root())
        subset = avalon.io.find_one({
            "type": "subset",
            "parent": context.data["assetDoc"]["_id"],
            "name": instance.data["subset"],
        })

        template_publish = project["config"]["template"]["publish"]
        template_data = {
            "root": root,
            "project": avalon.Session["AVALON_PROJECT"],
            "silo": avalon.Session["AVALON_SILO"],
            "asset": avalon.Session["AVALON_ASSET"],
            "subset": instance.data["subset"],
            "version": None
        }

        source = context.data["currentMaking"]
        source = context.data.get("originMaking") or source

        self.log = logging.getLogger(self.name)

        self._version_dir = ""

        self.context_data = context.data
        self.instance_data = instance.data
        self.subset = subset

        self.template_publish = template_publish
        self.template_data = template_data
        self.metadata = {
            "source": source,
            "mtime": os.path.getmtime(source),
            "fsize": os.path.getsize(source),
            "delegated": False,
            "succeeded": False,
        }

    def _metadata_path(self):
        return os.path.join(self._version_dir, self.META_FILE)

    def _is_available(self):
        if self.context_data.get("contractorAccepted"):
            return True

        metadata_path = self._metadata_path()

        if os.path.isfile(metadata_path):

            with open(metadata_path, "r") as fp:
                metadata = json.load(fp)

                if metadata["delegated"] or metadata["succeeded"]:
                    return False

        return True

    def write_metadata(self):
        metadata_path = self._metadata_path()
        with open(metadata_path, "w") as fp:
            json.dump(self.metadata, fp, indent=4)

    def clean_version_dir(self):
        """Create a clean version dir"""
        version_dir = self._version_dir

        if os.path.isdir(version_dir):
            self.log.info("Cleaning version dir.")

            for item in os.listdir(version_dir):
                item_path = os.path.join(version_dir, item)

                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)

                    elif os.path.isfile(item_path):
                        os.remove(item_path)

                except Exception as e:
                    self.log.debug(e)
                    return False

        else:
            os.makedirs(version_dir)

        return True

    def version_num(self):
        return self.template_data["version"]

    def version_dir(self):
        if self.context_data.get("contractorAccepted"):
            # version lock if publish process has been delegated.
            version_number = self.instance_data["versionNext"]
        else:
            version = None
            version_number = 1  # assume there is no version yet, start at 1
            if self.subset is not None:
                filter = {"type": "version", "parent": self.subset["_id"]}
                version = avalon.io.find_one(filter,
                                             projection={"name": True},
                                             sort=[("name", -1)])
            if version is not None:
                version_number += version["name"]

        version_template = os.path.dirname(self.template_publish)

        while True:
            self.template_data["version"] = version_number
            # Format dir
            version_dir = version_template.format(**self.template_data)
            version_dir = os.path.abspath(os.path.normpath(version_dir))

            self._version_dir = version_dir

            if not self._is_available():
                # Bump version
                version_number += 1
                continue

            else:
                success = self.clean_version_dir()
                if not success:
                    self.log.warning("Unable to cleanup previous "
                                     "version dir, trying next..")
                    continue

                self.write_metadata()
                break

        return version_dir

    def set_succeeded(self):
        use_contractor = self.instance_data.get("useContractor")
        accepted = self.context_data.get("contractorAccepted")
        on_delegate = use_contractor and not accepted

        if on_delegate:
            self.metadata["delegated"] = True
        else:
            self.metadata["succeeded"] = True

        self.write_metadata()


class ExtractVersionDirectory(pyblish.api.InstancePlugin):
    """Create publish version directory
    """

    label = "Create Version Directory"
    order = pyblish.api.ExtractorOrder - 0.4

    def process(self, instance):
        """Get a version dir which binded to current workfile
        """
        manager = VersionManager(instance)

        instance.data["versionDir"] = manager.version_dir()
        instance.data["versionNext"] = manager.version_num()

        instance.data["versionManager"] = manager
