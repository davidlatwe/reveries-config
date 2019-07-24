
import os
from collections import OrderedDict

import pyblish.api
import avalon.api
import avalon.io

from reveries import utils, lib
from reveries.plugins import PackageExtractor, skip_stage
# from reveries.maya.plugins import env_embedded_path


def to_tx(path):
    return os.path.splitext(path)[0] + ".tx"


def assemble_published_paths(previous_repr, previous_inventory):

    previous_by_fpattern = dict()

    if previous_inventory:

        parents = avalon.io.parenthood(previous_repr)
        _, subset, asset, project = parents

        _repr_path_cache = dict()

        for data in previous_inventory:
            tmp_data = dict()
            version_num = data["version"]

            if version_num in _repr_path_cache:
                repr_path = _repr_path_cache[version_num]

            else:
                version = {"name": version_num}
                parents = (version, subset, asset, project)
                repr_path = utils.get_representation_path_(previous_repr,
                                                           parents)
                _repr_path_cache[version_num] = repr_path

            tmp_data["pathMap"] = {
                fn: repr_path + "/" + fn for fn in data["fnames"]
            }
            # In case someone using published .tx file which coming from
            # loaded look...
            tmp_data["pathMapTx"] = {
                tx: repr_path + "/" + tx for tx in
                (to_tx(fn) for fn in data["fnames"])
            }

            fpattern = data["fpattern"]
            if fpattern not in previous_by_fpattern:
                previous_by_fpattern[fpattern] = list()

            previous_by_fpattern[fpattern].append((data, tmp_data))

    return previous_by_fpattern


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

        package_path = self.create_package()
        # package_path = env_embedded_path(package_path)

        # For storing calculated published file path for look or lightSet
        # extractors to update file path.
        if "fileNodeAttrs" not in self.context.data:
            self.context.data["fileNodeAttrs"] = OrderedDict()

        # Extract textures
        #
        self.log.info("Extracting textures..")

        self.use_tx = self.data.get("useTxMaps", False)

        file_inventory = list()
        previous_by_fpattern = dict()
        current_by_fpattern = dict()

        # Get previous files
        path = [
            avalon.api.Session["AVALON_PROJECT"],
            avalon.api.Session["AVALON_ASSET"],
            self.data["subset"],
            -1,  # latest version
            "TexturePack"
        ]
        representation_id = avalon.io.locate(path)
        if representation_id is not None:
            repr = avalon.io.find_one({"_id": representation_id})

            file_inventory = repr["data"].get("fileInventory", [])
            previous_by_fpattern = assemble_published_paths(repr,
                                                            file_inventory)

        # Get current files
        for data in self.data["fileData"]:
            file_node = data["node"]
            if file_node in self.data["fileNodesToIgnore"]:
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
        new_version = self.data["versionNext"]

        for fpattern, data in current_by_fpattern.items():
            if not data["fnames"]:
                raise RuntimeError("Empty file list, this is a bug.")

            file_nodes = [dat["node"] for dat in self.data["fileData"]
                          if dat["fpattern"] == fpattern]

            versioned_data = previous_by_fpattern.get(fpattern, list())
            versioned_data.sort(key=lambda (data, tmp): data["version"],
                                reverse=True)

            current_color_space = data["colorSpace"]

            for ver_data, tmp_data in versioned_data:

                previous_files = tmp_data["pathMap"]
                previous_txs = tmp_data["pathMapTx"]

                all_files = list()
                for file, abs_path in data["pathMap"].items():
                    if not (file in previous_files or file in previous_txs):
                        # Possible different file pattern
                        break  # Try previous version

                    _previous_tx = previous_txs.get(file)
                    abs_previous = previous_files.get(file, _previous_tx)

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
                    # resolved_path = env_embedded_path(resolved_path)
                    self.update_file_node_attrs(file_nodes,
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
                    self.add_file(abs_path, final_path)

                    if self.use_tx:
                        # Upload .tx file as well
                        tx_abs_path = to_tx(abs_path)
                        tx_final_path = to_tx(final_path)
                        self.add_file(tx_abs_path, tx_final_path)

                    all_files.append(file)

                head_file = sorted(all_files)[0]
                resolved_path = package_path + "/" + head_file
                self.update_file_node_attrs(file_nodes,
                                            resolved_path,
                                            current_color_space)

        self.add_data({"fileInventory": file_inventory})

    def update_file_node_attrs(self, file_nodes, path, color_space):
        from maya import cmds

        if self.use_tx:
            # Force downstream to use .tx map
            path = to_tx(path)

        for node in file_nodes:
            attr = node + ".fileTextureName"
            self.context.data["fileNodeAttrs"][attr] = path
            # Preserve color space values (force value after filepath change)
            # This will also trigger in the same order at end of context to
            # ensure after context it's still the original value.
            attr = node + ".colorSpace"
            self.context.data["fileNodeAttrs"][attr] = color_space

            # (NOTE) Force color space unlocked
            #        Previously we used to lock color space in case
            #        forgot to check it after changing file path.
            cmds.setAttr(attr, lock=False)
