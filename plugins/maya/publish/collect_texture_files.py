
import pyblish.api


class CollectTextureFiles(pyblish.api.InstancePlugin):
    """Collect texture data from each file nodes in instance

    Get file name pattern from file node and all files that exists in storage
    by the pattern string with color space setting.

    """

    order = pyblish.api.CollectorOrder + 0.4
    label = "Texture File Path"
    hosts = ["maya"]
    families = [
        "reveries.texture",
    ]

    def process(self, instance):
        import os
        from maya import cmds
        from maya.app.general.fileTexturePathResolver import (
            getFilePatternString,
            findAllFilesForPattern,
        )

        file_data = list()
        file_count = 0

        for file_node in instance:

            color_space = cmds.getAttr(file_node + ".colorSpace")
            tiling_mode = cmds.getAttr(file_node + ".uvTilingMode")
            is_sequence = cmds.getAttr(file_node + ".useFrameExtension")
            file_path = cmds.getAttr(file_node + ".fileTextureName",
                                     expandEnvironmentVariables=True)

            file_path = file_path.replace("\\", "/")
            dir_name = os.path.dirname(file_path)

            if not (is_sequence or tiling_mode):
                # (NOTE) If no sequence and no tiling, skip regex parsing
                #        to avoid potential not-regex-friendly file name which
                #        may lead to incorrect result.
                pattern = file_path
                all_files = [os.path.basename(pattern)]
            else:
                # (NOTE) When UV tiliing is enabled, if file name contains
                #        characters like `[]`, which possible from Photoshop,
                #        will make regex parse file name incorrectly.
                pattern = getFilePatternString(file_path,
                                               is_sequence,
                                               tiling_mode)
                all_files = [
                    os.path.basename(fpath) for fpath in
                    findAllFilesForPattern(pattern, frameNumber=None)
                ]

            if not all_files:
                self.log.error("%s file not exists." % file_node)
                continue

            fpattern = os.path.basename(pattern)

            if len(all_files) > 1:
                # If it's a sequence, include the dir name as the prefix
                # of the file pattern
                dir_name, seq_dir = os.path.split(dir_name)
                fpattern = seq_dir + "/" + fpattern
                all_files = [seq_dir + "/" + file for file in all_files]

            file_data.append({
                "node": file_node,
                "fpattern": fpattern,
                "colorSpace": color_space,
                "dir": dir_name,
                "fnames": all_files,
            })

            file_count += len(all_files)

        instance.data["fileData"] = file_data

        self.log.info("Collected %d texture files from %s file node."
                      "" % (file_count, len(file_data)))
