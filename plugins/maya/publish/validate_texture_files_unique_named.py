
import os
import pyblish.api
from reveries import plugins


class SelectInvalidFileNodes(plugins.MayaSelectInvalidInstanceAction):

    label = "Select Invalid"


class SelectInvalidOnFilePathEditor(plugins.SelectInvalidInstanceAction):

    label = "File Path Editor"

    def select(self, invalid):
        from maya import cmds, mel

        tmp_var = "$_reveries_action_plugin_tmpvar_"
        tmp_list = "$_reveries_action_plugin_tmplist_"

        # Open File Path Editor and set to show only resloved textures
        mel.eval("""
            FilePathEditor; filePathEditorWin;
            FPEupdateTreeView 1;
            FPEShowMenuCB None;
            FPEShowMenuCB Resolved;
            FPEShowMenuCB file;
        """)

        fpe_view = mel.eval("%s = $gFPETreeView;" % tmp_var)
        fpe_attr = mel.eval("string %(t)s[];"
                            "%(t)s = $gFPEFileAttributes;" % {"t": tmp_list})
        # Get file node item indices in view
        item_indices = list()
        for i, attr_name in enumerate(fpe_attr):
            node = attr_name[:-len(".fileTextureName")]
            if node in invalid:
                item_indices.append(i)

        if not item_indices:
            # This should not happen
            raise IndexError("Invalid file nodes can not be found in "
                             "File Path Editor.")

        # Expand 'Texture' item and select only invalid file node item
        parent_index = cmds.treeView(fpe_view,
                                     query=True,
                                     itemParent=item_indices[0])
        cmds.treeView(fpe_view, edit=True, expandItem=(parent_index, True))
        cmds.treeView(fpe_view, edit=True, clearSelection=True)
        for index in item_indices:
            cmds.treeView(fpe_view, edit=True, selectItem=(index, True))

    def deselect(self):
        from maya import cmds, mel

        tmp_var = "$_reveries_action_plugin_tmpvar_"

        fpe_window = mel.eval("%s = $gFPEWindowName;" % tmp_var)
        if cmds.window(fpe_window, query=True, exists=True):
            fpe_view = mel.eval("%s = $gFPETreeView;" % tmp_var)
            cmds.treeView(fpe_view, edit=True, clearSelection=True)


HYP_BIN_LIST = "defaultRenderGlobals.hyperShadeBinList"

PYBLISH_BIN_PREFIX = "pyb._."
PYBLISH_BIN_SUFFIX = "._.PYBLISH_TEMP_BINS"


def cleanup_bin_list(bin_list):
    if not bin_list:
        # No bin exists
        return

    new_bin_list = list()
    has_pyblish_bin = False

    for bin in bin_list.split(";"):
        if (bin.startswith(PYBLISH_BIN_PREFIX) and
                bin.endswith(PYBLISH_BIN_SUFFIX)):
            has_pyblish_bin = True
            continue

        new_bin_list.append(bin)

    return ";".join(new_bin_list) if has_pyblish_bin else None


class GroupingInvalidWithBin(pyblish.api.Action):

    label = "Hypershade Bins"
    on = "failed"
    icon = "tags"

    def process(self, context, plugin):
        errored_instances = plugins.get_errored_instances_from_context(context)

        all_invalid = dict()

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)
        for instance in instances:
            all_invalid.update(plugin.get_invalid(instance))

        if all_invalid:
            self.group_with_bins(all_invalid)
            self.show_hypershade_bins()
        else:
            self.cleanup()

    def show_hypershade_bins(self):
        from maya import mel
        # Show Hypershade window & refresh Bins
        mel.eval("""
            HypershadeWindow;
            evalDeferred(" \
            HypershadeOpenBinsWindow; \
            hypershadeOpenBinsWindow(`getFocusedHypershade`, true); \
            $form = hyperShadeBinUIForm(`getFocusedHypershade`); \
            refreshHyperShadeBinsUI($form, true); \
            ");
        """)

    @staticmethod
    def cleanup():
        from maya import cmds

        # Check Hypershade bins
        bin_list = cmds.getAttr(HYP_BIN_LIST)
        hyp_new_bin_list = cleanup_bin_list(bin_list)

        if hyp_new_bin_list is None:
            # Is clean
            return

        # Cleanup all file node's bin membership
        for node in cmds.ls(type="file"):
            attr = node + ".binMembership"
            if not cmds.objExists(attr):
                continue

            bin_list = cmds.getAttr(attr)
            new_bin_list = cleanup_bin_list(bin_list)
            if new_bin_list is not None:
                cmds.setAttr(attr, new_bin_list, type="string")

        # Cleanup Hypershade bins
        cmds.setAttr(HYP_BIN_LIST, hyp_new_bin_list, type="string")

    def group_with_bins(self, invalid):
        from maya import cmds
        from collections import defaultdict

        invalid_by_fpattern = defaultdict(list)

        for node, fpattern in invalid.items():
            invalid_by_fpattern[fpattern].append(node)

        for fpattern, nodes in invalid_by_fpattern.items():
            bin_name = PYBLISH_BIN_PREFIX + fpattern + PYBLISH_BIN_SUFFIX
            cmds.binMembership(nodes, addToBin=bin_name)


class ValidateTextureFilesUniqueNamed(pyblish.api.InstancePlugin):
    """Ensure texture file name unique

    Each file name (pattern) should be unique named, unless the duplicated
    name pattern were actually same image contents.

    """

    order = pyblish.api.ValidatorOrder
    label = "Texture Files Unique Named"
    hosts = ["maya"]
    families = [
        "reveries.texture",
    ]
    actions = [
        pyblish.api.Category("Select Invalid"),
        SelectInvalidFileNodes,
        SelectInvalidOnFilePathEditor,
        GroupingInvalidWithBin,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from reveries import lib

        # (NOTE) See the code below..
        instance.data["fileNodesToIgnore"] = set()

        dirs_by_fpattern = dict()

        for data in instance.data["fileData"]:
            fpattern = data["fpattern"]
            dir_name = data["dir"]

            if fpattern not in dirs_by_fpattern:
                dirs_by_fpattern[fpattern] = set()

            dirs_by_fpattern[fpattern].add(dir_name)

        # Same file/seq name (pattern) but in different folder
        duplicated_pattern = set()

        for fpattern, dirs in dirs_by_fpattern.items():
            if len(dirs) > 1:
                duplicated_pattern.add(fpattern)

        if len(duplicated_pattern) == 0:
            return []

        # Checking on possible duplicat named file/seq (pattern)

        duplicated_data = dict()

        for data in instance.data["fileData"]:
            fpattern = data["fpattern"]

            if fpattern in duplicated_pattern:
                if fpattern not in duplicated_data:
                    duplicated_data[fpattern] = list()

                duplicated_data[fpattern].append(data)

        # If the duplicated were actually the same content, they will be
        # forgiven, but only one of them will be extracted.

        consider_duplicated = set()

        for fpattern, dup_data in duplicated_data.items():

            # Checking on file count
            file_counts = set([len(data["fnames"]) for data in dup_data])
            if not len(file_counts) == 1:
                # File counts not matched, consider duplicated.
                consider_duplicated.add(fpattern)
                continue

            # Checking on each files' name, size and modification time
            file_matrix = set()

            for data in dup_data:
                dir_name = data["dir"]

                feature_set = list()

                for fname in data["fnames"]:
                    file_path = dir_name + "/" + fname

                    if not os.path.isfile(file_path):
                        # This plugin does not respond to missing files.
                        continue

                    fsize = os.path.getsize(file_path)
                    fmtime = lib.soft_mtime(file_path)

                    features = (fname, fsize, fmtime)
                    feature_set.append(features)

                file_matrix.add(tuple(feature_set))

                if len(file_matrix) > 1:
                    # File features not matched, consider duplicated.
                    consider_duplicated.add(fpattern)
                    break

            if fpattern not in consider_duplicated:
                # The duplicated were actually the same content, take only
                # one of them (shortest (`fpattern`, `node`)) and mark the
                # rest so we can ignore them while extracting.
                dup_data_sorted = sorted(
                    dup_data,
                    key=lambda data: (data["fpattern"], data["node"])
                )
                cls.log.warning("These file nodes will be ignored due to "
                                "content duplicated with '%s'"
                                "" % dup_data_sorted[0]["node"])

                # (NOTE) Normally, we do not collect data during validation,
                #        but we do need to mark those same content patterns
                #        so that we won't have to work twice in extraction.
                ignoring = instance.data["fileNodesToIgnore"]

                for node in (data["node"] for data in dup_data_sorted[1:]):
                    ignoring.add(node)
                    cls.log.info(node)

        if len(consider_duplicated) == 0:
            return []

        invalid = dict()

        for data in instance.data["fileData"]:
            fpattern = data["fpattern"]
            node = data["node"]

            if fpattern in consider_duplicated:
                invalid[node] = fpattern

        return invalid

    def process(self, instance):
        # Cleanup hypershade bins if any..
        GroupingInvalidWithBin.cleanup()

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Duplicate file name on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + file_node + "'" for file_node in invalid))
            )

            raise Exception("%s has different content but duplicate "
                            "file names." % instance)
