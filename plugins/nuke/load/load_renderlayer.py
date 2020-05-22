
import nuke
import avalon.api
from collections import OrderedDict
from avalon.nuke import pipeline, lib, command
from reveries.plugins import PackageLoader
from reveries.utils import get_representation_path_
from reveries.tools import seqparser
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

    def set_path(self, read, aov_name, path):
        read["file"].setValue(path)
        read["label"].setValue(aov_name)

    def set_range(self, read, start, end):
        start, end = int(start), int(end)
        read["first"].setValue(start)
        read["last"].setValue(end)
        read["origfirst"].setValue(start)
        read["origlast"].setValue(end)

    def set_format(self, read, resolution):
        w, h = resolution
        for format in nuke.formats():
            if format.width() == w and format.height() == h:
                try:
                    read["format"].setValue(format.name())
                except TypeError:
                    self.log.warning("Unrecognized format")
                finally:
                    break

    def is_singleaov(self, path):
        try:
            data = exrheader.read_exr_header(path)
        except Exception:
            self.log.warning("EXR header read failed: %s" % path)
            return False
        return set(data["channels"]) in [{"R", "G", "B", "A"},
                                         {"R", "G", "B"}]

    def load(self, context, name=None, namespace=None, options=None):

        representation = context["representation"]
        version = context["version"]
        asset = context["asset"]

        asset_name = asset["data"].get("shortName", asset["name"])
        families = context["subset"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        name = name or context["subset"]["name"]
        namespace = namespace or "%s_%s" % (asset_name, family_name)

        start = version["data"]["startFrame"]
        end = version["data"]["endFrame"]

        sequences = seqparser.show_on_stray(
            root=self.package_path,
            sequences=representation["data"]["sequence"],
            framerange=(start, end),
            parent=pipeline.get_main_window(),
        )

        # Filter out multi-channle sequence
        multiaovs = OrderedDict()
        singleaovs = OrderedDict()

        for aov_name in sorted(sequences, key=lambda k: k.lower()):
            data = sequences[aov_name]
            path = data["_resolved"] % start
            if self.is_singleaov(path):
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

            self.set_path(read, aov_name=aov_name, path=path)
            self.set_format(read, data["resolution"])
            self.set_range(read, start=start, end=end)

            # Mark aov name
            lib.set_avalon_knob_data(read, {("aov", "AOV"): aov_name})
            multiaov_reads.append(read)

        nodes = multiaov_reads[:]

        if singleaovs:
            has_beauty = "beauty" in singleaovs

            with command.viewer_update_and_undo_stop():
                group = nuke.createNode("Group")
                group.autoplace()

                with nuke_lib.group_scope(group):

                    for aov_name, data in singleaovs.items():
                        read = nuke.Node("Read")
                        read["selected"].setValue(False)
                        read.autoplace()
                        path = data["_resolved"]

                        self.set_path(read, aov_name=aov_name, path=path)
                        self.set_format(read, data["resolution"])
                        self.set_range(read, start=start, end=end)

                        # Mark aov name
                        lib.set_avalon_knob_data(read, {("aov", "AOV"): aov_name})
                        singleaov_reads[aov_name] = read

                    if has_beauty:
                        beauty = singleaov_reads.pop("beauty")
                    else:
                        beauty = singleaov_reads.popitem()[1]

                    nuke_lib.exr_merge(beauty, singleaov_reads.values())

                    output = nuke.createNode("Output")
                    output.autoplace()

                stamp = nuke.createNode("PostageStamp")
                stamp.setName(namespace)
                group.setName(name)

            nodes += [stamp, group] + group.nodes()

        return pipeline.containerise(name=name,
                                     namespace=namespace,
                                     nodes=nodes,
                                     context=context,
                                     loader=self.__class__.__name__,
                                     no_backdrop=True)

    def update(self, container, representation):
        read_nodes = dict()

        parents = avalon.io.parenthood(representation)
        version, subset, asset, project = parents

        self.package_path = get_representation_path_(representation, parents)

        for node in container["_members"]:
            if node.Class() == "Read":
                data = lib.get_avalon_knob_data(node)
                read_nodes[data["aov"]] = node

        start = version["data"]["startFrame"]
        end = version["data"]["endFrame"]

        sequences = seqparser.show_on_stray(
            root=self.package_path,
            sequences=representation["data"]["sequence"],
            framerange=(start, end),
            parent=pipeline.get_main_window(),
        )

        with lib.sync_copies(list(read_nodes.values())):
            for aov_name, data in sequences.items():
                read = read_nodes.get(aov_name)
                if not read:
                    continue

                self.set_path(read, aov_name=aov_name, path=data["_resolved"])
                self.set_format(read, data["resolution"])
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
