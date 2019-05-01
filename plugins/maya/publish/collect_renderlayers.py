
import os
from maya import cmds

import pyblish.api
from reveries.maya import lib, utils


def get_render_attr(attr, layer):
    return lib.query_by_renderlayer("defaultRenderGlobals",
                                    attr,
                                    layer)


class CollectRenderlayers(pyblish.api.InstancePlugin):
    """Gather instances by active render layers
    """

    order = pyblish.api.CollectorOrder - 0.299
    hosts = ["maya"]
    label = "Collect Renderlayers"
    families = [
        "reveries.imgseq.render"
    ]

    def process(self, instance):

        context = instance.context
        original = instance

        member = instance[:]
        member += cmds.listRelatives(member,
                                     allDescendents=True,
                                     fullPath=True) or []
        cameras = cmds.ls(member, type="camera", long=True)
        if not cameras:
            return

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
        collected = False
        for layer in renderlayers:

            render_cams = lib.ls_renderable_cameras(layer)

            if not set(cameras).intersection(set(render_cams)):
                continue
            collected = True

            self.log.debug("Creating instance for renderlayer: %s" % layer)

            # Check if layer is in valid (linked) layers
            if layer not in valid_layers:
                self.log.warning("%s is invalid, skipping" % layer)
                continue

            layer_members = cmds.editRenderLayerMembers(layer,
                                                        query=True,
                                                        fullNames=True)
            # (NOTE): Some of renderLayer member may not exists..
            layer_members = cmds.ls(layer_members)

            layername = lib.pretty_layer_name(layer)

            renderer = get_render_attr("currentRenderer", layer)
            name_preview = utils.compose_render_filename(layer)
            ext = os.path.splitext(name_preview)[-1]

            # Get layer specific settings, might be overrides
            data = {
                "renderlayer": layer,
                "startFrame": get_render_attr("startFrame", layer),
                "endFrame": get_render_attr("endFrame", layer),
                "byFrameStep": get_render_attr("byFrameStep", layer),
                "renderer": renderer,
                "fileNamePrefix": utils.get_render_filename_prefix(layer),
                "fileExt": ext,
                "renderCam": cameras,
            }

            data.update(original.data)

            data["families"] = self.families[:]
            data["dependencies"] = dict()
            data["futureDependencies"] = dict()

            data["subset"] += "." + layername
            data["category"] = "[{renderer}] {layer}".format(
                renderer=data["renderer"], layer=layername)

            instance = context.create_instance(data["subset"])
            instance.data.update(data)

            # Push renderlayer members into instance,
            # for collecting dependencies
            instance += layer_members

            # Assign contractor
            if instance.data["deadlineEnable"]:
                instance.data["useContractor"] = True
                instance.data["publishContractor"] = "deadline.maya.render"

            self.collect_output_paths(instance)

            # Set extract type (representation type)
            if len(instance.data["outputPaths"]) > 1:
                instance.data["extractType"] = "imageSequenceSet"
            else:
                instance.data["extractType"] = "imageSequence"

        if collected:
            # Original instance contain renderable camera,
            # we can safely remove it
            context.remove(original)
            # Sort by renderlayers, masterLayer will be on top
            L = (lambda i: i.data["subset"].split(".")[-1])
            context.sort(key=lambda i: 0 if L(i) == "masterLayer" else L(i))

    def collect_output_paths(self, instance):
        renderer = instance.data["renderer"]
        layer = instance.data["renderlayer"]
        output_dir = instance.context.data["outputDir"]
        cam = instance.data["renderCam"][0]

        instance.data["outputPaths"] = utils.get_output_paths(output_dir,
                                                              renderer,
                                                              layer,
                                                              cam)
