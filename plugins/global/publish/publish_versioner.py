
import os
import json
import shutil
import logging
import pyblish.api
import avalon.api
import avalon.io


class CollectPublishVersioner(pyblish.api.InstancePlugin):
    """
    """

    label = "Publish Versioner"
    order = pyblish.api.CollectorOrder + 0.49999999

    def process(self, instance):
        instance.data["versioner"] = PublishVersioner(instance)


class PublishVersioner(object):

    META_FILE = ".publish.meta.json"

    def __init__(self, instance):
        context = instance.context

        project = context.data["projectDoc"]
        root = instance.data.get("reprRoot", avalon.api.registered_root())

        template_publish = project["config"]["template"]["publish"]
        template_data = {
            "root": root,
            "project": avalon.Session["AVALON_PROJECT"],
            "silo": avalon.Session["AVALON_SILO"],
            "asset": avalon.Session["AVALON_ASSET"],
            "subset": instance.data["subset"],
        }

        source = context.data["currentMaking"]
        source = context.data.get("originMaking", source)

        if not os.path.exists(source):
            mtime = fsize = None
        else:
            mtime = os.path.getmtime(source)
            fsize = os.path.getsize(source)

        self.log = logging.getLogger("Version Manager")

        self._template_publish = template_publish
        self._template_data = template_data

        self._version_dir = ""
        self._version_num = 0
        self._data = instance.data
        self._metadata = {
            "source": source,
            "mtime": mtime,
            "fsize": fsize,
            "delegated": False,
            "succeeded": False,
        }
        self._contractor_accepted = context.data.get("contractorAccepted")
        self._asset_id = context.data["assetDoc"]["_id"]

    def __repr__(self):
        return "PublishVersioner(versionNum: %03d, versionDir: %s)" % (
            self._version_num, self._version_dir)

    def _metadata_path(self):
        return os.path.join(self._version_dir, self.META_FILE)

    def _is_in_remote_session(self):
        # Will be deprecated
        return bool(self._contractor_accepted)

    def _is_about_to_remote(self):
        # Will be deprecated
        is_to_remote = bool(self._data.get("useContractor"))
        return is_to_remote and not self._is_in_remote_session()

    def _is_available(self):
        if self._is_in_remote_session():
            return True

        metadata_path = self._metadata_path()

        if os.path.isfile(metadata_path):

            with open(metadata_path, "r") as fp:
                metadata = json.load(fp)

                if metadata["delegated"] or metadata["succeeded"]:
                    return False

        return True

    def _write_metadata(self):
        metadata_path = self._metadata_path()
        with open(metadata_path, "w") as fp:
            json.dump(self._metadata, fp, indent=4)

    def _clean_version_dir(self):
        """Create a clean version dir"""
        if self._is_in_remote_session():
            return True

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
        return self._version_num

    def version_dir(self):
        if self._is_in_remote_session():
            # version lock if publish process has been delegated.
            version_number = self._data["versionNext"]
        else:
            version = None
            version_number = 1  # assume there is no version yet, start at 1

            subset = avalon.io.find_one({
                "type": "subset",
                "parent": self._asset_id,
                "name": self._data["subset"],
            })

            if subset is not None:
                filter = {"type": "version", "parent": subset["_id"]}
                version = avalon.io.find_one(filter,
                                             projection={"name": True},
                                             sort=[("name", -1)])
            if version is not None:
                version_number += version["name"]

        version_template = os.path.dirname(self._template_publish)

        while True:
            # Format dir
            version_dir = version_template.format(version=version_number,
                                                  **self._template_data)
            version_dir = os.path.abspath(os.path.normpath(version_dir))

            self._version_num = version_number
            self._version_dir = version_dir

            if not self._is_available():
                # Bump version
                version_number += 1
                continue

            else:
                success = self._clean_version_dir()
                if not success:
                    self.log.warning("Unable to cleanup previous "
                                     "version dir, trying next..")
                    continue

                break

        self._write_metadata()

        return version_dir

    def representation_dir(self, name):
        return self._template_publish.format(version=self._version_num,
                                             representation=name,
                                             **self._template_data)

    def set_succeeded(self):
        if self._is_about_to_remote():
            state = "delegated"
        else:
            state = "succeeded"

        self._metadata[state] = True
        self._write_metadata()
