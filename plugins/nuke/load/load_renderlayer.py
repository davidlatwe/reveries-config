
import nuke
import avalon.api
from collections import OrderedDict
from avalon.nuke import pipeline, lib, command
from reveries.plugins import PackageLoader
from reveries.utils import get_representation_path_
from reveries.nuke import lib as nuke_lib
from reveries.vendor import parse_exr_header as exrheader


class RenderLayerLoader(PackageLoader, avalon.api.Loader):

    label = "Load RenderLayer"
    icon = "camera-retro"
    color = "#28EDC9"

    hosts = ["nuke"]

    families = ["reveries.renderlayer"]

    representations = [
        "renderLayer",
    ]

    @classmethod
    def set_path(cls, read, aov_name, path):
        read["file"].setValue(path.format(stereo="%V"))
        read["label"].setValue(aov_name)

    @classmethod
    def set_range(cls, read, start, end):
        start, end = int(start), int(end)
        read["first"].setValue(start)
        read["last"].setValue(end)
        read["origfirst"].setValue(start)
        read["origlast"].setValue(end)

    @classmethod
    def set_format(cls, read, resolution):
        w, h = resolution
        for format in nuke.formats():
            if format.width() == w and format.height() == h:
                try:
                    read["format"].setValue(format.name())
                except TypeError:
                    cls.log.warning("Unrecognized format")
                finally:
                    break

    @classmethod
    def pick_beauty(cls, channels, group_name):
        from avalon.tools import widgets
        from avalon.vendor import qargparse

        options = [
            qargparse.Enum(name="beauty",
                           label="Beauty As",
                           items=sorted(channels.keys()),
                           default=0,
                           help="Select a default channel for exr_merge.")
        ]
        dialog = widgets.OptionDialog()
        dialog.setWindowTitle("Pick Beauty - %s" % group_name)
        dialog.setMinimumWidth(300)
        dialog.create(options)

        if not dialog.exec_():
            return
        # Get option
        options = dialog.parse()
        return options.get("beauty")

    @classmethod
    def is_singleaov(cls, path, start):
        import os

        path = path % start

        if "{stereo}" in path:
            for side in ["Left", "Right"]:
                _p = path.format(stereo=side)
                if os.path.isfile(_p):
                    path = _p
                    break
            else:
                message = "Stereo not found in: %s" % path
                nuke.critical(message)  # This will pop-up a dialog
                raise RuntimeError(message)

        try:
            data = exrheader.read_exr_header(path)
        except Exception:
            cls.log.warning("EXR header read failed: %s" % path)
            return False
        return set(data["channels"]) in [{"R", "G", "B", "A"},
                                         {"R", "G", "B"}]

    @classmethod
    def resolve_path(cls, sequences, root_path):
        import os

        for aov_name, data in sequences.items():
            if "fname" in data:
                tail = "%s/%s" % (aov_name, data["fname"])
            else:
                tail = data["fpattern"]

            padding = tail.count("#")
            if padding:
                frame_str = "%%0%dd" % padding
                tail = tail.replace("#" * padding, frame_str)

            path = os.path.join(root_path, tail).replace("\\", "/")
            data["_resolved"] = path

    @classmethod
    def build_sequences(cls,
                        sequences,
                        root_path,
                        group_name,
                        stamp_name,
                        start,
                        end):

        cls.resolve_path(sequences, root_path)

        # Filter out multi-channle sequence
        multiaovs = OrderedDict()
        singleaovs = OrderedDict()

        for aov_name in sorted(sequences, key=lambda k: k.lower()):
            data = sequences[aov_name]
            if cls.is_singleaov(data["_resolved"], start):
                singleaovs[aov_name] = data
            else:
                multiaovs[aov_name] = data

        multiaov_reads = list()
        singleaov_reads = OrderedDict()

        lib.reset_selection()

        for aov_name, data in multiaovs.items():
            read = nuke.Node("Read")
            read["selected"].setValue(False)
            read.autoplace()
            path = data["_resolved"]

            cls.set_path(read, aov_name=aov_name, path=path)
            # cls.set_format(read, data["resolution"])
            cls.set_range(read, start=start, end=end)

            # Mark aov name
            lib.set_avalon_knob_data(read, {("aov", "AOV"): aov_name})
            multiaov_reads.append(read)

        nodes = multiaov_reads[:]

        if singleaovs:

            if "beauty" in singleaovs:
                # Default channel (RGBA) for exr_merge
                beauty_name = "beauty"
            else:
                # Ask artist if want to assign a beauty if not found
                beauty_name = cls.pick_beauty(singleaovs, group_name)

            with command.viewer_update_and_undo_stop():
                group = nuke.createNode("Group")
                group.autoplace()

                with nuke_lib.group_scope(group):

                    for aov_name, data in singleaovs.items():
                        read = nuke.Node("Read")
                        read["selected"].setValue(False)
                        read.autoplace()
                        path = data["_resolved"]

                        cls.set_path(read, aov_name=aov_name, path=path)
                        # cls.set_format(read, data["resolution"])
                        cls.set_range(read, start=start, end=end)

                        # Mark aov name
                        knob = ("aov", "AOV")
                        lib.set_avalon_knob_data(read, {knob: aov_name})
                        singleaov_reads[aov_name] = read

                    if beauty_name:
                        beauty = singleaov_reads.pop(beauty_name)
                    else:
                        beauty = singleaov_reads.popitem()[1]

                    nuke_lib.exr_merge(beauty, singleaov_reads.values())

                    output = nuke.createNode("Output")
                    output.autoplace()

                stamp = nuke.createNode("PostageStamp")
                stamp.setName(stamp_name)
                group.setName(group_name)

            nodes += [stamp, group] + group.nodes()

        return nodes

    def _fallback_stage(self, representation, version):
        """Workaround for sequence integration failed in remote publish"""
        root = avalon.api.registered_root()
        root = representation["data"].get("reprRoot", root)
        work_dir = version["data"]["workDir"].format(root=root)
        stage_path = work_dir + "/renders"

        message = ("Published path not exists, fallback to stage path:\n"
                   "    %s\n"
                   " -> %s" % (self.package_path, stage_path))
        self.log.warning(message)

        return stage_path

    def load(self, context, name=None, namespace=None, options=None):
        import os

        representation = context["representation"]
        version = context["version"]
        asset = context["asset"]

        asset_name = asset["data"].get("shortName", asset["name"])
        families = context["subset"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        name = name or context["subset"]["name"]
        namespace = namespace or "%s_%s" % (asset_name, family_name)

        sequences = representation["data"]["sequence"]
        start = version["data"]["startFrame"]
        end = version["data"]["endFrame"]

        if os.path.isdir(self.package_path):
            sequence_root = self.package_path
        else:
            sequence_root = self._fallback_stage(representation, version)

        nodes = self.build_sequences(sequences,
                                     sequence_root,
                                     group_name=name,
                                     stamp_name=namespace,
                                     start=start,
                                     end=end,)

        return pipeline.containerise(name=name,
                                     namespace=namespace,
                                     nodes=nodes,
                                     context=context,
                                     loader=self.__class__.__name__,
                                     no_backdrop=True)

    def update(self, container, representation):
        import os

        read_nodes = dict()

        parents = avalon.io.parenthood(representation)
        version, subset, asset, project = parents

        self.package_path = get_representation_path_(representation, parents)

        sequences = representation["data"]["sequence"]
        start = version["data"]["startFrame"]
        end = version["data"]["endFrame"]

        if os.path.isdir(self.package_path):
            sequence_root = self.package_path
        else:
            sequence_root = self._fallback_stage(representation, version)

        self.resolve_path(sequences, sequence_root)

        for node in container["_members"]:
            if node.Class() == "Read":
                data = lib.get_avalon_knob_data(node)
                read_nodes[data["aov"]] = node

        with lib.sync_copies(list(read_nodes.values())):
            for aov_name, data in sequences.items():
                read = read_nodes.get(aov_name)
                if not read:
                    # (TODO) Create Read node for new or removed AOV.
                    continue

                self.set_path(read, aov_name=aov_name, path=data["_resolved"])
                # self.set_format(read, data["resolution"])
                self.set_range(read, start=start, end=end)

        node = container["_node"]
        with lib.sync_copies([node], force=True):
            asset_name = asset["data"].get("shortName", asset["name"])
            families = subset["data"]["families"]  # avalon-core:subset-3.0
            family_name = families[0].split(".")[-1]

            update = {
                "name": subset["name"],
                "representation": str(representation["_id"]),
                "namespace": "%s_%s" % (asset_name, family_name)
            }
            pipeline.update_container(node, update)

    def remove(self, container):
        nodes = list(container["_members"])
        nodes.append(container["_node"])

        delete_bin = list()
        for node in nodes:
            for copy in lib.find_copies(node):
                delete_bin.append(copy)
            delete_bin.append(node)

        with command.viewer_update_and_undo_stop():
            for node in delete_bin:
                try:
                    nuke.delete(node)
                except ValueError:
                    pass
