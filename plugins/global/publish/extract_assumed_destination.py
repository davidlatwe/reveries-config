
import os
import shutil
import pyblish.api
import avalon.api
import avalon.io


class ExtractAssumedDestination(pyblish.api.InstancePlugin):
    """Generate the assumed destination path where the file will be stored"""

    label = "Assumed Destination"
    order = pyblish.api.ExtractorOrder - 0.4

    LOCK = ".publish.lock"

    def process(self, instance):

        context = instance.context

        project = context.data["projectDoc"]
        root = instance.data.get("reprRoot", avalon.api.registered_root())

        template_publish = project["config"]["template"]["publish"]
        template_data = {
            "root": root,
            "project": avalon.api.Session["AVALON_PROJECT"],
            "silo": avalon.api.Session["AVALON_SILO"],
            "asset": avalon.api.Session["AVALON_ASSET"],
            "subset": instance.data["subset"],
        }

        version = None
        version_num = 1  # assume there is no version yet, start at 1
        version_pinned = "versionPin" in instance.data
        is_progressive = context.data.get("_progressivePublishing")

        subset = avalon.io.find_one({
            "type": "subset",
            "parent": context.data["assetDoc"]["_id"],
            "name": instance.data["subset"],
        })

        if subset is not None and not version_pinned:
            filter = {"type": "version", "parent": subset["_id"]}
            version = avalon.io.find_one(filter,
                                         projection={"name": True},
                                         sort=[("name", -1)])
        if version is not None:
            version_num += version["name"]

        if version_pinned:
            version_num = instance.data["versionPin"]

        version_template = os.path.dirname(template_publish)

        # Probe version

        def is_version_locked(lock):
            """Is version locked by other ?"""
            if os.path.isfile(lock):
                with open(lock, "r") as f:
                    return f.read().strip() != context.data["user"]
            return False

        def lock_version(lock):
            with open(lock, "w") as f:
                f.write(context.data["user"])

        while True:
            # Format dir
            template_data["version"] = version_num
            version_dir = version_template.format(**template_data)
            version_dir = os.path.abspath(os.path.normpath(version_dir))

            lockfile = version_dir + "/" + self.LOCK
            version_locked = is_version_locked(lockfile)

            if not version_pinned and version_locked:
                # Bump version
                version_num += 1
                continue

            elif is_progressive and version_locked:
                # In progressive publish mode, publish will be triggered
                # multiple times with files that only be part of sequence,
                # so we wouldn't want nor need to clear the version every
                # time it runs.
                break

            else:
                if not os.path.isdir(version_dir):
                    os.makedirs(version_dir)

                lock_version(lockfile)

                success = self.clean_dir(version_dir)
                if not success:
                    if version_pinned:
                        raise Exception("Version dir cleanup failed: %s"
                                        % version_dir)
                    else:
                        self.log.warning("Version dir cleanup failed, "
                                         "try next..")
                        continue

                break

        self.log.info("Version %03d will be created for %s" %
                      (version_num, instance))

        instance.data["publishPathTemplateData"] = template_data
        instance.data["publishPathTemplate"] = template_publish

        instance.data["_versionlock"] = lockfile
        instance.data["versionNext"] = version_num
        instance.data["versionDir"] = version_dir

        template_work = project["config"]["template"]["work"]
        instance.data["_sharedStage"] = self.shared_stage(template_work, root)

    def clean_dir(self, path):
        """Create a clean version dir"""
        success = True

        self.log.info("Cleaning version dir.")

        keep = [
            self.LOCK,
            ".instance.json",  # Instance dump file
        ]

        for item in os.listdir(path):
            if item in keep:
                continue

            item_path = os.path.join(path, item)

            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)

                elif os.path.isfile(item_path):
                    os.remove(item_path)

            except Exception as e:
                self.log.debug(e)

                return not success

        return success

    def shared_stage(self, template_work, root):
        """Create a stage folder that is in the same root as publish path

        This *shared* stage path enables using hardlink to integrate files and
        remote publishing.

        (NOTE) The path formation method is referenced from Avalon module,
               `avalon.pipeline._format_work_template`

        """
        import getpass

        shared = template_work.format(**{
            "root": root,
            "project": avalon.api.Session["AVALON_PROJECT"],
            "silo": avalon.api.Session["AVALON_SILO"],
            "asset": avalon.api.Session["AVALON_ASSET"],
            "task": avalon.api.Session["AVALON_TASK"],
            "app": avalon.api.Session["AVALON_APP"],

            # Optional
            "user": avalon.api.Session.get("AVALON_USER", getpass.getuser()),
            "hierarchy": avalon.api.Session.get("AVALON_HIERARCHY"),
        })

        shared_stage = shared + "/_stage"
        if not os.path.isdir(shared_stage):
            os.makedirs(shared_stage)

        return shared_stage
