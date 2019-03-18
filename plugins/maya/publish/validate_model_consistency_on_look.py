
import pyblish.api

from avalon import io
from reveries.maya import utils
from maya import cmds


class ValidateModelConsistencyOnLook(pyblish.api.InstancePlugin):
    """Ensure model UUID consistent and unchanged in LookDev
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "LookDev Model Consistency"
    families = [
        "reveries.look",
    ]

    model_family = "reveries.model"
    rig_family = "reveries.rig"

    def process(self, instance):

        if "xgen" in instance.data["subset"].lower():
            self.log.info("No need to check on XGen look.")
            return

        elif "rig" in instance.data["subset"].lower():
            # rig's look
            self.log.info("Checking on rig.")
            FAMILY = self.rig_family
            repr_name = "mayaBinary"
        else:
            # model's look
            self.log.info("Checking on model.")
            FAMILY = self.model_family
            repr_name = "mayaBinary"

        collected_profiles = dict()

        asset = instance.context.data["assetDoc"]
        for subset in io.find({"type": "subset", "parent": asset["_id"]}):
            latest = io.find_one({"type": "version", "parent": subset["_id"]},
                                 sort=[("name", -1)])
            if FAMILY not in latest["data"]["families"]:
                continue

            # Get representation
            representation = io.find_one({"type": "representation",
                                          "parent": latest["_id"],
                                          "name": repr_name})
            profile = representation["data"]["modelProfile"]
            collected_profiles[subset["name"]] = profile

        if not collected_profiles:
            # Model not even published before, this is not right.
            raise Exception("No model for this look has been published "
                            "before, please publish model first.")

        uuid_required = instance.data["requireAvalonUUID"]

        # Hash current model and collect Avalon UUID
        geo_id_and_hash = dict()
        hasher = utils.MeshHasher()
        warned = False
        for transform in uuid_required:
            # It must be one mesh paring to one transform.
            mesh = cmds.listRelatives(transform,
                                      shapes=True,
                                      noIntermediate=True,
                                      fullPath=True)[0]
            id = utils.get_id(transform)
            if id is None:
                if not warned:
                    self.log.warning("Some mesh has no Avalon UUID.")
                    warned = True
                continue

            hasher.set_mesh(mesh)
            hasher.update_points()
            hasher.update_normals()
            hasher.update_uvmap()
            # id must be unique, no other should have same id.
            geo_id_and_hash[id] = hasher.digest()
            hasher.clear()

        matched = list()
        for name, profile in collected_profiles.items():
            current_ids = set(geo_id_and_hash.keys())
            previous_ids = set(profile.keys())

            if current_ids.issuperset(previous_ids):
                self.log.info("Match found: %s" % name)
                matched.append(name)
            else:
                self.log.debug("Not matched: %s" % name)

        if not matched:
            # Is the model being published ?
            model_instances = [i for i in instance.context
                               if (i.data["family"] == self.model_family and
                                   i.data.get("publish", True))]
            for inst in model_instances:
                if set(inst).issuperset(set(uuid_required)):
                    self.log.info("Model is being published.")
                    break
                else:
                    self.log.debug("Instance not match.")
            else:
                raise Exception("Current models UUID is not consistent with "
                                "previous published version.\n"
                                "Please update your loaded model, or publish "
                                "it if you are the model author.")
        else:
            # Checking on mesh hashes
            changed_on = list()
            for id, hash in geo_id_and_hash.items():
                for match in matched:
                    if id not in collected_profiles[match]:
                        continue

                    if not collected_profiles[match][id] == hash:
                        changed_on.append(match)

            if changed_on:
                self.log.warning("Some model has been modified, the look "
                                 "may not apply correctly on these subsets: ")
                for changed in changed_on:
                    self.log.warning(changed)
