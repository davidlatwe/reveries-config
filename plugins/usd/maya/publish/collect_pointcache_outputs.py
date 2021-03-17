import json

from avalon import io
import pyblish.api


class CollectPointcacheUSDOutputs(pyblish.api.InstancePlugin):
    """Get container from ROOT group and get asset data from db.
    Generate child pointcache instance if rigging reference multiple models.
    """

    order = pyblish.api.CollectorOrder + 0.4992
    label = "Collect Pointcache USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache.usd"
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def process(self, instance):
        from reveries.maya import lib, pipeline
        from reveries.common.task_check import task_check

        _skip_msg = "Please turn off \"exportAniUSDData\" to skip USD publish."

        if instance.data.get("isDummy"):
            return

        if not instance.data.get("exportPointCacheUSD", False):
            return

        if not instance.data.get("geometry_path", ""):
            self.log.error(
                "Missing geometry group in hierarchy. {}".format(_skip_msg)
            )
            raise Exception("%s <Geometry Check> Failed." % instance)

        # Check container exists
        out_caches = instance.data.get("all_cacheables")

        self.rig_namespace = lib.get_ns(out_caches[0]).split(":")[1]
        container = pipeline.get_container_from_namespace(self.rig_namespace)

        if not container:
            self.log.error(
                "{}: Please check your rig referenced from Avalon Loader.".format(instance))
            raise Exception("Get container failed: {}".format(instance))

        # Check asset exists
        asset_data = self._check_asset_exists(container)
        if not asset_data:
            raise Exception("Can't found asset: {} in this show.".format(
                container))

        # Get model subset data from publish
        self.model_subset_data = self.__get_rig_pub_data(container)
        if not self.model_subset_data:
            self.log.error(
                "{}: Can't get model subset data from rig publish. "
                "Please check your rig already published usd.".format(instance))
            raise Exception("Get model subset data failed: {}".format(instance))

        asset_id = asset_data['_id']
        self.parent_asset_name = asset_data.get('name', '')
        instance.data["asset_name"] = self.parent_asset_name
        instance.data["asset_id"] = asset_id

        # Check task
        if task_check(task_name="animating"):
            instance.data["subsetGroup"] = "Animation"

        # Create children pointcache instance
        geometry_path = instance.data["geometry_path"]
        self._get_child_subset(instance, geometry_path, out_caches)

    def _get_child_subset(self, instance, geometry_path, out_caches):
        import maya.cmds as cmds

        # Get children
        children = cmds.listRelatives(geometry_path, children=True)
        if len(children) == 1:
            instance.data["usd_outCache"] = out_caches
            return

        skip_parent = False
        self.invalid_grp = []
        for child_name in children:

            # Get asset data
            asset_id, look_variant = self.__get_model_subset_data(child_name)
            if not asset_id or not look_variant:
                continue

            # Get asset data
            _filter = {"type": "asset", "_id": io.ObjectId(asset_id)}
            asset_data = io.find_one(_filter)

            if not asset_data:
                self.invalid_grp.append(child_name)
                _msg = "{}: Cant get model's asset data from db.". \
                    format(child_name)
                self.log.error(_msg)
                continue

            child_asset_name = asset_data.get('name', '')
            # Get child cache
            child_cache = [cache for cache in out_caches if child_name in cache]
            if not child_cache:
                continue

            if not skip_parent:
                instance.data["usd_outCache"] = child_cache
                instance.data["look_variant"] = look_variant
                skip_parent = True
                continue

            # Get subset name
            subset_name = "pointcache.{}.{}".format(
                instance.data["subset"].replace("pointcache.", ""),
                child_name.split(":")[-1]
            )

            self.__create_child_instance(
                instance,
                subset_name=subset_name,
                asset_name=child_asset_name,
                asset_id=asset_id,
                caches=child_cache,
                look_variant=look_variant
            )

        if self.invalid_grp:
            raise Exception(
                "%s <Check children subset usd> Failed."
                "Please check your models are from publish." % instance
            )

    def __create_child_instance(
            self, instance, subset_name=None, asset_id=None,
            asset_name=None, caches=None, look_variant=None):
        # Create new instance
        context = instance.context
        backup = instance

        if not self.ins_exists(context, subset_name):
            _family = "reveries.pointcache.child.usd"
            parent_pointcache_name = instance.data["subset"]

            _instance = context.create_instance(subset_name)
            context.remove(_instance)
            context.insert(0, _instance)

            _instance.data.update(backup.data)

            _instance.data["family"] = _family
            _instance.data["families"] = []
            _instance.data["subset"] = subset_name

            _instance.data["asset_name"] = asset_name
            _instance.data["asset_id"] = asset_id
            _instance.data["outCache"] = caches
            _instance.data["usd_outCache"] = caches
            _instance.data["subsetGroup"] = "USD"
            _instance.data["parent_pointcache_name"] = parent_pointcache_name
            _instance.data["look_variant"] = look_variant

    def __get_rig_pub_data(self, container):
        import maya.cmds as cmds
        from reveries.common import get_publish_files

        model_subset_data = {}
        rig_subset_id = cmds.getAttr("{}.subsetId".format(container))

        # Get data from skeleton publish
        rig_data = io.find_one({"_id": io.ObjectId(rig_subset_id)})

        _filter = {
            "name": "{}Skeleton".format(rig_data["name"]),
            "parent": rig_data["parent"]
        }
        rig_prim_data = io.find_one(_filter)

        if rig_prim_data:
            model_subset_json = get_publish_files.get_files(
                rig_prim_data["_id"], key='modelDataFileName').get("USD", "")
            if model_subset_json:
                with open(model_subset_json, "r") as file:
                    _pub_data = json.load(file)
                model_subset_data = _pub_data.get("model_data", {})

        # Get data from rig publish
        if not model_subset_data:
            _filter = {
                "type": "version",
                "parent": io.ObjectId(rig_subset_id),
            }
            version_data = io.find_one(_filter, sort=[("name", -1)])
            model_subset_data = version_data["data"].get(
                "model_subset_data", {})

        return model_subset_data

    def __get_model_subset_data(self, child_name):
        asset_id = ""
        look_variant = ""

        try:
            # Get asset/model subset id
            _model_group = child_name.replace("{}:".format(
                self.rig_namespace), "")
            if _model_group in self.model_subset_data.keys():
                asset_id = self.model_subset_data[_model_group]["asset_id"]
                model_subset_id = self.model_subset_data[_model_group]["subset_id"]

                _filter = {
                    "type": "subset",
                    "data.families": "reveries.look",
                    "data.model_subset_id": model_subset_id}
                lookdev_data = io.find_one(_filter)

                if lookdev_data:
                    look_variant = lookdev_data["name"]
        except Exception as e:
            print("{}: Get container failed: {}".format(child_name, e))

        if not asset_id:
            asset_id = self.__get_asset_id_from_model_group_old_way(child_name)

        return asset_id, look_variant

    def __get_asset_id_from_model_group_old_way(self, child_name):
        import maya.cmds as cmds

        child_root_group = ""

        _child_groups = cmds.listRelatives(
            child_name, allDescendents=True, type="transform", fullPath=True)

        if not _child_groups:
            return

        for _group in _child_groups:
            if _group.endswith(":ROOT"):
                child_root_group = _group
                break

        if not child_root_group:
            return False

        if not cmds.attributeQuery(
                'AvalonID', node=child_root_group, exists=True):
            self.invalid_grp.append(child_name)
            _msg = "{}: Missing \"AvalonID\" attribute on ROOT group. ". \
                format(child_name)
            self.log.error(_msg)
            return False

        asset_id = cmds.getAttr(
            "{}.AvalonID".format(child_root_group)).split(":")[0]
        return asset_id

    def _check_asset_exists(self, container):
        import maya.cmds as cmds

        asset_id = cmds.getAttr('{}.assetId'.format(container))
        _filter = {"type": "asset", "_id": io.ObjectId(asset_id)}
        asset_data = io.find_one(_filter)

        return asset_data
