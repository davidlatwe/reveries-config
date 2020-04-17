
import os
import nuke
import avalon.api
from avalon.nuke import pipeline, lib
from reveries.plugins import PackageLoader
from reveries.utils import get_representation_path_


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

    def load(self, context, name=None, namespace=None, options=None):

        representation = context["representation"]
        version = context["version"]

        start = version["data"]["startFrame"]
        end = version["data"]["endFrame"]

        nodes = list()

        for aov_name, data in representation["data"]["sequence"].items():
            read = nuke.Node("Read")
            nodes.append(read)

            tail = data.get("fpattern", "%s/%s" % (aov_name, data["fname"]))
            path = os.path.join(self.package_path, tail).replace("\\", "/")

            self.set_path(read, aov_name=aov_name, path=path)
            self.set_format(read, data["resolution"])
            self.set_range(read, start=start, end=end)

            # Mark aov name
            lib.set_avalon_knob_data(read, {("aov", "AOV"): aov_name})

        asset = context["asset"]

        asset_name = asset["data"].get("shortName", asset["name"])
        families = context["subset"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        namespace = namespace or "%s_%s" % (asset_name, family_name)
        pipeline.containerise(name=context["subset"]["name"],
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

        with lib.sync_copies(list(read_nodes.values())):
            for aov_name, data in representation["data"]["sequence"].items():
                read = read_nodes.get(aov_name)
                if not read:
                    continue

                self.set_path(read, aov_name=aov_name, file_name=data["fname"])
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

        for node in nodes:
            for copy in lib.find_copies(node):
                nuke.delete(copy)
            nuke.delete(node)
