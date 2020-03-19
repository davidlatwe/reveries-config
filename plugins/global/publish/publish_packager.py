
import os
import shutil
import logging
import pyblish.api
import avalon.api
import avalon.io
from reveries import utils


class CollectPublishPackager(pyblish.api.InstancePlugin):
    """
    """

    label = "Publish Packager"
    order = pyblish.api.CollectorOrder + 0.49999999

    def process(self, instance):
        instance.data["packager"] = PublishPackager(instance)


class PublishPackager(object):
    """Handling representations' extraction ground works
    """

    LOCK = "/.publish.lock"

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

        self.log = logging.getLogger("Version Manager")

        self._template_publish = template_publish
        self._template_data = template_data

        self._version_dir = ""
        self._version_num = 0
        self._subset_name = instance.data["subset"]
        self._asset_id = context.data["assetDoc"]["_id"]

        if "packages" not in instance.data:
            instance.data["packages"] = dict()  # representations' data
        if "extractors" not in instance.data:
            instance.data["extractors"] = list()  # delayed extractors
        if "files" not in instance.data:
            instance.data["files"] = list()
        if "hardlinks" not in instance.data:
            instance.data["hardlinks"] = list()

        self._data = instance.data

        self._representation = None
        self._skip_stage = False

    def __repr__(self):
        return "PublishPackager()"

    def _clean_version_dir(self):
        """Create a clean version dir"""
        success = True
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

                    return not success
        else:
            os.makedirs(version_dir)

        return success

    def lock(self):
        open(self._version_dir + self.LOCK, "w").close()

    def unlock(self):
        os.remove(self._version_dir + self.LOCK)

    def is_locked(self):
        return os.path.isfile(self._version_dir + self.LOCK)

    def version_num(self):
        return self._version_num

    def version_dir(self):
        version = None
        version_number = 1  # assume there is no version yet, start at 1

        subset = avalon.io.find_one({
            "type": "subset",
            "parent": self._asset_id,
            "name": self._subset_name,
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

            if self.is_locked():
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

        self.lock()

        return version_dir

    def representation_dir(self, name):
        return self._template_publish.format(version=self._version_num,
                                             representation=name,
                                             **self._template_data)

    def create_package(self, with_representation=True):
        """Create representation stage dir

        Register and create a staging directory for extraction usage later on.

        MUST call this in every representation's extraction process.

        The default staging directory is generated by `tempfile.mkdtemp()` with
        "pyblish_tmp_" prefix, but if the extraction method get decorated with
        `skip_stage`, the staging directory will be the publish directory.

        Args:
            with_representation (bool): Whether to append representation dir to
                                        the end of the staging path.
                                        Default True.

        Return:
            pkg_dir (str): staging directory

        """
        staging_dir = self._data.get("stagingDir", None)

        if not staging_dir:
            if self._skip_stage:
                staging_dir = self._data["versionDir"]
            else:
                staging_dir = utils.temp_dir(prefix="pyblish_tmp_")

            self._data["stagingDir"] = staging_dir

        if with_representation:
            pkg_dir = os.path.join(staging_dir, self._representation)
        else:
            pkg_dir = staging_dir

        repr_dir = self.representation_dir(self._representation)

        if not os.path.isdir(pkg_dir):
            os.makedirs(pkg_dir)

        # Reset
        self._skip_stage = False

        # Init representation entries
        if self._representation not in self._data["packages"]:
            self._data["packages"][self._representation] = dict()

        self.add_data({
            "packageDir": pkg_dir,
            "representationDir": repr_dir,
        })

        return pkg_dir

    def set_representation(self, representation):
        self._representation = representation

    def skip_stage(self):
        """Make extractor directly save to publish dir

        This will make `create_package()` return representation's
        versioned dir in publish space.

        And the `instance.data["stagingDir"]` will be set to versioned dir
        instead of random dir in temp folder. So there should be no file/dir
        copy while intergation since the representation already exists in
        final destination.

        """
        self._skip_stage = True

    def file_name(self, extension="", suffix=""):
        """Convenient method for composing file name with default format"""
        extension = ("." + extension) if extension else ""
        return "{subset}{suffix}{ext}".format(subset=self._data["subset"],
                                              suffix=suffix,
                                              ext=extension)

    def add_data(self, data):
        """Add/Update data to representation

        Arguments:
            data (dict): Additional representation data

        """
        package_data = self._data["packages"][self._representation]
        utils.deep_update(package_data, data)

    def add_file(self, src, dst):
        """Add file to copy queue

        Arguments:
            src (str): Source file path
            dst (str): The path that file needs to be copied to

        """
        self._data["files"].append((src, dst))

    def add_hardlink(self, src, dst):
        """Add file to hardlink queue

        Arguments:
            src (str): Source file path
            dst (str): The path that file needs to be hardlinked to

        """
        self._data["hardlinks"].append((src, dst))

    def _extractor_delayer(self, object, function, args, kwargs, each_frame):
        """Append extractor and input args into delay queue"""
        extractor = {
            "representation": self._representation,
            "obj": object,
            "func": function,
            "args": args,
            "kwargs": kwargs,
            "eachFrame": each_frame,
            "_done": False,
        }
        self._data["extractors"].append(extractor)

    def delayed_extractors(self):
        """Yield delayed and unprocess extractors"""
        for extractor in self._data["extractors"]:
            if extractor["_done"]:
                continue
            yield extractor
