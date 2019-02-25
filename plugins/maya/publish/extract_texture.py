
import os

import pyblish.api
import avalon.api
import avalon.io

from reveries.plugins import PackageExtractor, skip_stage
from reveries.maya.plugins import env_embedded_path
from reveries.utils import AssetHasher


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
        from maya.app.general.fileTexturePathResolver import (
            getFilePatternString,
            findAllFilesForPattern,
        )

        package_path = self.create_package()
        package_path = env_embedded_path(package_path)

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

        processed = dict()

        # Hash file to check which to copy and which to remain old link
        for file_node in self.member:

            tiling_mode = cmds.getAttr(file_node + ".uvTilingMode")
            is_sequence = cmds.getAttr(file_node + ".useFrameExtension")
            img_path = cmds.getAttr(file_node + ".fileTextureName",
                                    expandEnvironmentVariables=True)

            pattern = getFilePatternString(img_path, is_sequence, tiling_mode)

            if pattern in processed:
                final_pattern_path = processed[pattern]
                SKIP = True

            else:

                img_name = os.path.basename(pattern)
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
                final_pattern_path = os.path.join(*paths)

                processed[pattern] = final_pattern_path
                SKIP = False

            self.context.data["fileNodePath"][file_node] = final_pattern_path
            self.log.debug("FileNode: {!r}".format(file_node))
            self.log.debug("Texture Path: {!r}".format(final_pattern_path))

            if SKIP:
                continue

            # Files to be transfered
            curreent_files = findAllFilesForPattern(pattern, None)

            hasher = AssetHasher()
            for file in curreent_files:
                hasher.add_file(file)
            hash_value = hasher.digest()

            try:

                previous_pattern = latest_hashes[hash_value]

            except KeyError:
                latest_hashes[hash_value] = final_pattern_path

                for file in curreent_files:
                    img_name = os.path.basename(file)
                    paths.pop()
                    paths.append(img_name)
                    final_path = os.path.join(*paths)

                    self.add_file(file, final_path)

            else:
                previous_files = findAllFilesForPattern(previous_pattern, None)

                for file in previous_files:
                    img_name = os.path.basename(file)
                    paths.pop()
                    paths.append(img_name)
                    final_path = os.path.join(*paths)

                    self.add_hardlink(file, final_path)

        self.add_data({"hashes": latest_hashes})
