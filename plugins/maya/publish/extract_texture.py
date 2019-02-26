
import os

import pyblish.api
import avalon.api
import avalon.io

from reveries.plugins import PackageExtractor, skip_stage
from reveries.maya.plugins import env_embedded_path
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

        processed_pattern = dict()

        # Hash file to check which to copy and which to remain old link
        for file_node in self.member:

            tiling_mode = cmds.getAttr(file_node + ".uvTilingMode")
            is_sequence = cmds.getAttr(file_node + ".useFrameExtension")
            img_path = cmds.getAttr(file_node + ".fileTextureName",
                                    expandEnvironmentVariables=True)

            pattern = getFilePatternString(img_path, is_sequence, tiling_mode)
            img_name = os.path.basename(img_path)

            if pattern in processed_pattern:

                final_pattern = processed_pattern[pattern]

                dir_name = os.path.dirname(final_pattern)
                final_path = os.path.join(dir_name, img_name)
                SKIP = True

            else:

                paths = [package_path]
                paths += file_node.split(":")  # Namespace as fsys hierarchy
                paths.append(os.path.basename(pattern))  # image pattern name
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
                final_pattern = os.path.join(*paths)
                processed_pattern[pattern] = final_pattern

                paths.pop()  # Change to file path from fileNode
                paths.append(img_name)
                final_path = os.path.join(*paths)
                SKIP = False

            self.context.data["fileNodePath"][file_node] = final_path
            self.log.info("FileNode: {!r}".format(file_node))
            self.log.info("Texture Path: {!r}".format(final_pattern))

            if SKIP:
                self.log.info("Skipped.")
                continue

            # Files to be transfered
            curreent_files = findAllFilesForPattern(pattern, None)
            self.log.debug("File count: {}".format(len(curreent_files)))

            for file in curreent_files:
                hash_value = hash_file(file)

                img_name = os.path.basename(file)
                paths.pop()  # Change to resloved file path
                paths.append(img_name)
                final_path = os.path.join(*paths)

                try:

                    published_file = latest_hashes[hash_value]
                    _expand = os.path.expandvars(published_file)
                    if not os.path.isfile(_expand):
                        self.log.warning("Published file not exists, "
                                         "copy new one. ({})"
                                         "".format(_expand))
                        # Jump to add file
                        raise KeyError("Published file not exists.")

                except KeyError:

                    latest_hashes[hash_value] = final_path
                    self.add_file(file, final_path)
                    self.log.debug("File added: {0} -> {1}"
                                   "".format(file, final_path))

                else:
                    self.add_hardlink(published_file, final_path)
                    self.log.debug("Hardlink added: {0} -> {1}"
                                   "".format(file, final_path))

        self.add_data({"hashes": latest_hashes})
