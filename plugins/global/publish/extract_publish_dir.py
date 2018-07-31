
import os
import pyblish.api
import avalon.api
import avalon.io


class ExtractPublishDir(pyblish.api.InstancePlugin):
    """
    Does not create publish dir, only generate the path.
    """

    label = "Publish Dir"
    order = pyblish.api.ExtractorOrder - 0.499

    def process(self, instance):

        # Required environment variables
        PROJECT = avalon.api.Session["AVALON_PROJECT"]
        ASSET = instance.data["asset"]
        SUBSET = instance.data["subset"]

        project = avalon.io.find_one(
            {"type": "project"}, projection={"config.template.publish": True})

        asset = avalon.io.find_one({"type": "asset",
                                    "name": ASSET,
                                    "parent": project["_id"]})

        assert all([project, asset]), ("Could not find current project or "
                                       "asset '%s'" % ASSET)

        subset = avalon.io.find_one({"type": "subset",
                                     "name": SUBSET,
                                     "parent": asset["_id"]})

        # get version
        if instance.context.data.get("contractor_accepted"):
            # version lock if publish process has been delegated.
            version_number = instance.data["version_next"]
        else:
            # assume there is no version yet, we start at `1`
            version = None
            version_number = 1
            if subset is not None:
                version = avalon.io.find_one({"type": "version",
                                              "parent": subset["_id"]},
                                             {"name": True},
                                             sort=[("name", -1)])

            # if there is a subset there ought to be version
            if version is not None:
                version_number += version["name"]

        root = avalon.api.registered_root()
        template_data = {"root": root,
                         "project": PROJECT,
                         "silo": asset['silo'],
                         "asset": ASSET,
                         "subset": SUBSET,
                         "version": version_number}

        template_publish = project["config"]["template"]["publish"]

        publish_dir = os.path.dirname(template_publish).format(**template_data)
        # Clean the path
        publish_dir = os.path.abspath(os.path.normpath(publish_dir))

        instance.data["asset_id"] = asset["_id"]
        instance.data["template"] = (template_data, template_publish)
        instance.data["publish_dir"] = publish_dir
        instance.data["version_next"] = version_number
