
import os
from collections import OrderedDict

import pyblish.api
import avalon.api
import avalon.io

from reveries import lib
from reveries.plugins import PackageExtractor
from reveries.maya.plugins import env_embedded_path
from reveries.maya import lib as maya_lib


def to_tx(path):
    return os.path.splitext(path)[0] + ".tx"


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

    def extract_TexturePack(self, instance):

        packager = instance.data["packager"]
        packager.skip_stage()
        package_path = packager.create_package()
        package_path = env_embedded_path(package_path)

        # For storing calculated published file path for look or lightSet
        # extractors to update file path.
        if "fileNodeAttrs" not in instance.data:
            instance.data["fileNodeAttrs"] = OrderedDict()

        # Extract textures
        #
        self.log.info("Extracting textures..")

        self.use_tx = instance.data.get("useTxMaps", False)

        file_inventory = list()
        previous_by_fpattern = dict()
        current_by_fpattern = dict()

        # Get previous files
        path = [
            avalon.api.Session["AVALON_PROJECT"],
            avalon.api.Session["AVALON_ASSET"],
            instance.data["subset"],
            -1,  # latest version
            "TexturePack"
        ]
        representation_id = avalon.io.locate(path)
        if representation_id is not None:
            repr = avalon.io.find_one({"_id": representation_id})

            file_inventory = repr["data"].get("fileInventory", [])
            _ = maya_lib.resolve_file_profile(repr, file_inventory)
            previous_by_fpattern = _

        # Get current files
        for data in instance.data["fileData"]:
            file_node = data["node"]
            if file_node in instance.data["fileNodesToIgnore"]:
                continue

            dir_name = data["dir"]
            fnames = data["fnames"]
            fpattern = data["fpattern"]

            current_by_fpattern[fpattern] = {
                "node": data["node"],
                "colorSpace": data["colorSpace"],
                "fnames": fnames,
                "pathMap": {fn: dir_name + "/" + fn for fn in fnames},
            }

        # To transfer
        #
        new_version = instance.data["versionNext"]

        for fpattern, data in current_by_fpattern.items():
            if not data["fnames"]:
                raise RuntimeError("Empty file list, this is a bug.")

            file_nodes = [dat["node"] for dat in instance.data["fileData"]
                          if dat["fpattern"] == fpattern]

            versioned_data = previous_by_fpattern.get(fpattern, list())
            versioned_data.sort(key=lambda elem: elem[0]["version"],
                                reverse=True)  # elem: (data, tmp_data)

            current_color_space = data["colorSpace"]

            for ver_data, tmp_data in versioned_data:

                previous_files = tmp_data["pathMap"]

                all_files = list()
                for file, abs_path in data["pathMap"].items():
                    if file not in previous_files:
                        # Possible different file pattern
                        break  # Try previous version

                    abs_previous = previous_files.get(file, "")

                    if not os.path.isfile(abs_previous):
                        # Previous file not exists (should not happen)
                        break  # Try previous version

                    # Checking on file size and modification time
                    same_file = lib.file_cmp(abs_path, abs_previous)
                    if not same_file:
                        # Possible new files
                        break  # Try previous version

                    all_files.append(file)

                else:
                    # Version matched, consider as same file
                    head_file = sorted(all_files)[0]
                    resolved_path = abs_previous[:-len(file)] + head_file
                    resolved_path = env_embedded_path(resolved_path)
                    self.update_file_node_attrs(instance,
                                                file_nodes,
                                                resolved_path,
                                                current_color_space)
                    # Update color space
                    # * Although files may be the same, but color space may
                    #   changed by artist.
                    # * We only keep track the color space, not apply them
                    #   from database.
                    ver_data["colorSpace"] = current_color_space

                    # Proceed to next pattern
                    break

            else:
                # Not match with any previous version, consider as new file
                self.log.info("New texture collected from '%s': %s"
                              "" % (data["node"], fpattern))

                file_inventory.append({
                    "fpattern": fpattern,
                    "version": new_version,
                    "colorSpace": current_color_space,
                    "fnames": data["fnames"],
                })

                all_files = list()
                for file, abs_path in data["pathMap"].items():
                    final_path = package_path + "/" + file
                    packager.add_file(abs_path, final_path)

                    if self.use_tx:
                        # Upload .tx file as well
                        tx_abs_path = to_tx(abs_path)
                        tx_final_path = to_tx(final_path)
                        packager.add_file(tx_abs_path, tx_final_path)

                    all_files.append(file)

                head_file = sorted(all_files)[0]
                resolved_path = package_path + "/" + head_file
                self.update_file_node_attrs(instance,
                                            file_nodes,
                                            resolved_path,
                                            current_color_space)

        packager.add_data({"fileInventory": file_inventory})

    def update_file_node_attrs(self, instance, file_nodes, path, color_space):
        # (NOTE) All input `file_nodes` will be set to same `color_space`
        from reveries.maya import lib

        for node in file_nodes:
            attr = node + ".fileTextureName"
            instance.data["fileNodeAttrs"][attr] = path
            # Preserve color space values (force value after filepath change)
            # This will also trigger in the same order at end of context to
            # ensure after context it's still the original value.
            attr = node + ".colorSpace"
            instance.data["fileNodeAttrs"][attr] = color_space

            attr = node + ".ignoreColorSpaceFileRules"
            instance.data["fileNodeAttrs"][attr] = True

            if lib.hasAttr(node, "aiAutoTx"):
                # Although we ensured the tx update, but the file modification
                # time still may loose during file transfer and trigger another
                # tx update later on. So we force disable it on each published
                # file node.
                attr = node + ".aiAutoTx"
                instance.data["fileNodeAttrs"][attr] = False
