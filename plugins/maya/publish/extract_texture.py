
import os

import pyblish.api
import avalon.api
import avalon.io

from reveries.plugins import PackageExtractor, skip_stage
from reveries.utils import hash_file


class ExtractTexture(PackageExtractor):
    """Export texture files
    """

    label = "Extract Texture"
    order = pyblish.api.ExtractorOrder - 0.1  # Run before look extractor
    hosts = ["maya"]
    families = ["reveries.texture"]

    representations = [
        "TexturePack"
    ]

    @skip_stage
    def extract_TexturePack(self):

        from maya import cmds

        package_path = self.create_package(None)

        package_path = package_path.replace(
            avalon.api.registered_root(), "$AVALON_PROJECTS"
        )

        if "fileNodePath" not in self.context.data:
            self.context.data["fileNodePath"] = dict()

        # Extract textures
        #
        self.log.info("Extracting textures..")

        # Get latest hashes
        path = [
            avalon.api.Session["AVALON_PROJECT"],
            avalon.api.Session["AVALON_ASSET"],
            self.data["subset"],
            -1,  # latest version
            "TexturePack"
        ]
        representation = avalon.io.locate(path)
        if representation is None:
            # Never been published
            latest_hashes = dict()
        else:
            representation = avalon.io.find_one({"_id": representation})
            latest_hashes = representation["data"]["hashes"]

        # Hash file to check which to copy and which to remain old link
        for file_node in self.member:
            attr_name = file_node + ".fileTextureName"
            img_path = cmds.getAttr(attr_name,
                                    expandEnvironmentVariables=True)

            img_name = os.path.basename(img_path)
            paths = [package_path]
            paths += file_node.split(":")  # Namespace as fsys hierarchy
            paths.append(img_name)  # image name
            #
            # Include node name as part of the path should prevent
            # file name collision which may introduce by two or
            # more file nodes sourcing from different directory
            # with same file name but different file content.
            #
            # For example:
            #   File_A.fileTextureName = "asset/a/texture.png"
            #   File_B.fileTextureName = "asset/b/texture.png"
            #
            final_path = os.path.join(*paths)

            hash_value = hash_file(img_path)
            try:
                previous_path = latest_hashes[hash_value]
            except KeyError:
                latest_hashes[hash_value] = final_path
                self.data["files"].append((img_path, final_path))
            else:
                self.data["hardlinks"].append((previous_path, final_path))

            self.context.data["fileNodePath"][file_node] = final_path
            self.log.debug("FileNode: {!r}".format(file_node))
            self.log.debug("Texture Path: {!r}".format(final_path))

        self.add_data({"hashes": latest_hashes})
