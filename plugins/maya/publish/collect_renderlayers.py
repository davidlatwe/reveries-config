
import os
from maya import cmds
from collections import OrderedDict

import pyblish.api
from reveries.plugins import context_process
from reveries.maya import lib, utils


def get_render_attr(attr, layer):
    return lib.query_by_renderlayer("defaultRenderGlobals",
                                    attr,
                                    layer)


def set_extraction_type(instance):
    if len(instance.data["outputPaths"]) > 1:
        instance.data["extractType"] = "imageSequenceSet"
    else:
        instance.data["extractType"] = "imageSequence"


class CollectRenderlayers(pyblish.api.InstancePlugin):
    """Gather instances by active render layers
    """

    order = pyblish.api.CollectorOrder - 0.299
    hosts = ["maya"]
    label = "Avalon Instances (Render)"
    families = ["reveries.imgseq"]

    @context_process
    def process(self, context):

        original = None
        # Remove all dummy `imgseq` instances
        for instance in list(context):
            if instance.data["family"] in self.families:

                original = instance.data.get("objectName")

                context.remove(instance)
        assert original is not None, "This is a bug."

        # Get all valid renderlayers
        # This is how Maya populates the renderlayer display
        rlm_attribute = "renderLayerManager.renderLayerId"
        connected_layers = cmds.listConnections(rlm_attribute) or []
        valid_layers = set(connected_layers)

        # Context data
        workspace = context.data["workspaceDir"]
        context.data["outputDir"] = os.path.join(workspace, "renders")
        # Are there other renderlayer than defaultRenderLayer ?
        context.data["hasRenderLayers"] = len(valid_layers) > 1
        # Using Render Setup system ?
        context.data["usingRenderSetup"] = lib.is_using_renderSetup()

        # Get all renderable renderlayers (not referenced)
        renderlayers = sorted(lib.ls_renderable_layers(),
                              key=lambda l:  # By renderlayer displayOrder
                              cmds.getAttr("%s.displayOrder" % l))

        # Create instance by renderlayers

        for layer in renderlayers:

            self.log.debug("Creating instance for renderlayer: %s" % layer)

            # Check if layer is in valid (linked) layers
            if layer not in valid_layers:
                self.log.warning("%s is invalid, skipping" % layer)
                continue

            layer_members = cmds.editRenderLayerMembers(layer, query=True)
            layer_members = cmds.ls(layer_members, long=True)
            layer_members += cmds.listRelatives(layer_members,
                                                allDescendents=True,
                                                fullPath=True) or []

            layername = lib.pretty_layer_name(layer)

            renderer = get_render_attr("currentRenderer", layer)
            name_preview = utils.compose_render_filename(layer)
            ext = os.path.splitext(name_preview)[-1]

            # Get layer specific settings, might be overrides
            data = {
                "objectName": original,
                "renderlayer": layer,
                "startFrame": get_render_attr("startFrame", layer),
                "endFrame": get_render_attr("endFrame", layer),
                "byFrameStep": get_render_attr("byFrameStep", layer),
                "renderer": renderer,
                "fileNamePrefix": utils.get_render_filename_prefix(layer),
                "fileExt": ext,
                "renderCam": lib.ls_renderable_cameras(layer),
            }

            by_layer = (lambda a: lib.query_by_renderlayer(original, a, layer))
            data.update({k: by_layer(k) for k in [
                "asset",
                "subset",
                "renderType",
                "deadlineEnable",
                "deadlinePool",
                "deadlineGroup",
                "deadlinePriority",
                "deadlineFramesPerTask",
            ]})

            render_type = data["renderType"]
            data["family"] = "reveries.imgseq"
            data["families"] = ["reveries.imgseq." + render_type]

            # For dependency tracking
            data["dependencies"] = dict()
            data["futureDependencies"] = dict()

            instance = context.create_instance(layername)
            instance.data.update(data)

            # Push renderlayer members into instance,
            # for collecting dependencies
            instance += list(set(layer_members))

            variate = getattr(self, "process_" + render_type)
            variate(instance, layer)

    def process_playblast(self, instance, layer):
        """
        """
        # Update subset name with layername
        instance.data["subset"] += "." + instance.name

        instance.data["category"] = "Playblast"

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"

    def process_render(self, instance, layer):
        """
        """
        # Update subset name with layername
        instance.data["subset"] += "." + instance.name

        instance.data["category"] = "Render: " + instance.data["renderer"]

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.render"

        self.collect_output_paths(instance)
        set_extraction_type(instance)

    def collect_output_paths(self, instance):
        renderer = instance.data["renderer"]
        layer = instance.data["renderlayer"]

        paths = OrderedDict()

        if renderer == "vray":
            import reveries.maya.vray.utils as utils_
            aov_names = utils_.get_vray_element_names(layer)

        elif renderer == "arnold":
            import reveries.maya.arnold.utils as utils_
            aov_names = utils_.get_arnold_aov_names(layer)

        else:
            aov_names = [""]

        output_dir = instance.context.data["outputDir"]

        for aov in aov_names:
            output_prefix = utils.compose_render_filename(layer, aov)
            output_path = output_dir + "/" + output_prefix

            paths[aov] = output_path.replace("\\", "/")

            self.log.debug("Collecting AOV output path: %s" % aov)
            self.log.debug("                      path: %s" % paths[aov])

        instance.data["outputPaths"] = paths
