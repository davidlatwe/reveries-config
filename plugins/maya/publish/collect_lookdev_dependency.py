
import pyblish.api


class CollectLookDevDependency(pyblish.api.InstancePlugin):
    """

    """

    order = pyblish.api.CollectorOrder + 0.21

    label = "Collect LookDev Dependency"
    hosts = ["maya"]
    families = [
        "reveries.look"
    ]

    # TODO:
    #   validate loaded model is latest, if using old model is a MUST,
    #   check comment for "**PUBLISHED WITH OLD MODEL**"

    def process(self, instance):
        import maya.cmds as cmds
        from collections import defaultdict
        from reveries.maya import utils

        id_required = instance.data["requireAvalonUUID"][:]

        def is_referenced(n):
            return cmds.referenceQuery(n, isNodeReferenced=True)

        referenced = list()
        in_scene = list()
        nodes_by_id = defaultdict(list)
        for full_path in id_required:
            _id = utils.get_id(full_path)

            nodes_by_id[_id].append(full_path)
            if is_referenced(full_path):
                referenced.append(full_path)
            else:
                in_scene.append(full_path)

        if (all(len(nodes) == 2 for nodes in nodes_by_id.values())
                and len(referenced) == len(in_scene)):
            # Valid
            self.log.info("Publishing lookDev with in-scene model, "
                          "and with published model referenced, "
                          "and all id matched.")

            self.filter_out_referenced(instance, referenced)

        elif len(referenced) and not len(in_scene):
            # Valid
            self.log.info("Publishing lookDev with only referenced model.")

        elif not len(referenced) and not len(in_scene):
            # Invalid
            self.log.warning("No model to collect lookDev")

        elif not len(referenced) and len(in_scene):
            # Invalid
            self.log.warning("Publishing lookDev with in-scene model, "
                             "but without latest model referenced.")

        else:
            # Invalid
            self.log.warning("Referenced published model might be outdated, "
                             "or in-scene model should be published first.")

            self.filter_out_referenced(instance, referenced)

        subset_ids = list(self.collect_model_subset(referenced))
        if len(subset_ids):
            instance.data["model_subset_id"] = subset_ids[0]
            if len(subset_ids) > 1:
                self.log.warning("Multiple model subset collected.")

    def collect_model_subset(self, nodes):
        from maya import cmds
        from reveries.maya import pipeline

        for _member in nodes:
            base_name = _member.split("|")[-1]
            if ":" in base_name:
                namespace = base_name.rsplit(":", 1)[0]
                self.log.debug("namespace: ", namespace)

                container = pipeline.get_container_from_namespace(namespace)
                if cmds.getAttr("{}.loader".format(container)) == "ModelLoader":
                    subset_id = cmds.getAttr("{}.subsetId".format(container))

                    yield subset_id

    def filter_out_referenced(self, instance, referenced):
        from maya import cmds

        for full_path in referenced:
            # filter out referenced
            instance.data["requireAvalonUUID"].remove(full_path)
            instance.data["dagMembers"].remove(full_path)
            for child in cmds.listRelatives(full_path,
                                            children=True,
                                            fullPath=True) or []:
                instance.data["dagMembers"].remove(child)
