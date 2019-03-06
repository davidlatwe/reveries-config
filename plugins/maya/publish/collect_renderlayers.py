
import os
from maya import cmds
from collections import OrderedDict

import pyblish.api
from avalon import io, maya
from reveries.plugins import context_process
from reveries.maya import lib, utils
from reveries.utils import get_versions_from_sourcefile


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

    def get_render_attr(self, attr, layer):
        return lib.query_by_renderlayer("defaultRenderGlobals",
                                        attr,
                                        layer)

    def get_pipeline_attr(self, layer):
        pipeline_attrs = [
            "asset",
            "subset",
            "renderType",
            "deadlineEnable",
            "deadlinePool",
            "deadlineGroup",
            "deadlinePriority",
            "deadlineFramesPerTask",
        ]
        return {k: lib.query_by_renderlayer(self.instance_node,
                                            k,
                                            layer)
                for k in pipeline_attrs}

    @context_process
    def process(self, context):

        self.instance_node = None

        # Remove all dummy `imgseq` instances
        for instance in list(context):
            if instance.data["family"] in self.families:
                self.instance_node = instance.data.get("objectName")
                context.remove(instance)

        assert self.instance_node is not None, "This is a bug."

        HAS_OTHER_NON_IMGSEQ_INSTANCES = bool(len(context))
        CONTRACTOR_ACCEPTED = context.data.get("contractorAccepted")

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
        if context.data["mayaVersion"] >= 2016.5:
            context.data["usingRenderSetup"] = cmds.mayaHasRenderSetup()
        else:
            context.data["usingRenderSetup"] = False

        # Create instance by renderlayers

        # Get all renderlayers and check their state
        renderlayers = [i for i in cmds.ls(type="renderLayer") if
                        cmds.getAttr("{}.renderable".format(i)) and not
                        cmds.referenceQuery(i, isNodeReferenced=True)]
        # By renderlayer displayOrder
        for layer in sorted(renderlayers,
                            key=lambda l: cmds.getAttr("%s.displayOrder" % l)):

            self.log.debug("Creating instance for renderlayer: %s" % layer)

            # Check if layer is in valid (linked) layers
            if layer not in valid_layers:
                self.log.warning("%s is invalid, skipping" % layer)
                continue

            if layer.endswith("defaultRenderLayer"):
                layername = "masterLayer"
            else:
                layername = layer

            renderer = self.get_render_attr("currentRenderer", layer)
            name_preview = utils.compose_render_filename(layer)
            ext = os.path.splitext(name_preview)[-1]

            # Get layer specific settings, might be overrides
            data = {
                "objectName": self.instance_node,
                "renderlayer": layer,
                "startFrame": self.get_render_attr("startFrame", layer),
                "endFrame": self.get_render_attr("endFrame", layer),
                "byFrameStep": self.get_render_attr("byFrameStep", layer),
                "renderer": renderer,
                "fileNamePrefix": utils.get_render_filename_prefix(layer),
                "fileExt": ext,
                "renderCam": lib.ls_renderable_cameras(layer),
            }

            data.update(self.get_pipeline_attr(layer))

            instance = context.create_instance(layername)
            # (NOTE) The instance is empty
            instance.data.update(data)

            # (NOTE) If there are other non-imgseq instances need to be
            #        published, wait for them.
            instance.data["publishOnLock"] = (HAS_OTHER_NON_IMGSEQ_INSTANCES or
                                              CONTRACTOR_ACCEPTED)

            # For dependency tracking
            instance.data["dependencies"] = dict()
            instance.data["futureDependencies"] = dict()

            instance.data["family"] = "reveries.imgseq"
            instance.data["families"] = list()
            variate = getattr(self, "process_" + instance.data["renderType"])
            variate(instance, layer)

            # Collect renderlayer members
            layer_members = cmds.editRenderLayerMembers(layer, query=True)
            members = cmds.ls(layer_members, long=True)
            members += cmds.listRelatives(members,
                                          allDescendents=True,
                                          fullPath=True) or []

            instance += list(set(members))

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

    def previous_published(self, instance):
        project = instance.context.data["projectDoc"]["name"]
        source = instance.context.data["currentMaking"]
        return get_versions_from_sourcefile(source, project)

    def process_playblast(self, instance, layer):
        """
        """
        # Update subset name with layername
        instance.data["subset"] += "." + instance.name

        # Inject shadow family
        instance.data["families"] = ["reveries.imgseq.playblast"]
        instance.data["category"] = "Playblast"

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"

        if instance.data["publishOnLock"] and maya.is_locked():
            # Collect previous published for dependency tracking
            for v in self.previous_published(instance):
                subset = io.find_one({"_id": v["parent"]}, {"name": True})
                instance.data["futureDependencies"][subset["name"]] = v["_id"]

    def process_lookdev(self, instance, layer):
        """
        """
        self.log.debug("Renderlayer: " + layer)

        lookdevs = lib.lsAttrs({"id": "pyblish.avalon.instance",
                                "family": "reveries.look",
                                "renderlayer": layer})
        lookdev_name = ""
        # There should be only one matched lookdev instance.
        # But let's not make this assumption here.
        for lookdev in lookdevs:
            lookdev_name = cmds.getAttr(lookdev + ".subset")
            self.log.debug("Look: " + lookdev_name)

        # Update subset name with lookDev name
        instance.data["subset"] += "." + lookdev_name

        # Inject shadow family
        instance.data["families"] = ["reveries.imgseq.lookdev"]
        instance.data["category"] = "lookdev: " + instance.data["renderer"]

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.render"

        if instance.data["publishOnLock"] and maya.is_locked():
            # Collect previous published for dependency tracking
            for v in self.previous_published(instance):
                subset = io.find_one({"_id": v["parent"]}, {"name": True})
                if ("reveries.look" in v["families"] and
                        not subset["name"] == lookdev_name):
                    # Filter out not related `look`
                    continue
                instance.data["futureDependencies"][subset["name"]] = v["_id"]

        self.collect_output_paths(instance)
        set_extraction_type(instance)

    def process_render(self, instance, layer):
        """
        """
        # Update subset name with layername
        instance.data["subset"] += "." + instance.name

        # Inject shadow family
        instance.data["families"] = ["reveries.imgseq.render"]
        instance.data["category"] = "Render: " + instance.data["renderer"]

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.render"

        if instance.data["publishOnLock"] and maya.is_locked():
            # Collect previous published for dependency tracking
            for v in self.previous_published(instance):
                subset = io.find_one({"_id": v["parent"]}, {"name": True})
                instance.data["futureDependencies"][subset["name"]] = v["_id"]

        self.collect_output_paths(instance)
        set_extraction_type(instance)
