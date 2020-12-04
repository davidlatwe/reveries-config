import avalon
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
        from reveries.maya import lib

        _skip_msg = "Please turn off \"exportAniUSDData\" to skip USD publish."

        if instance.data.get("isDummy"):
            return

        if not instance.data.get("geometry_path", ""):
            self.log.error(
                "Missing geometry group in hierarchy. {}".format(_skip_msg)
            )
            raise Exception("%s <Geometry Check> Failed." % instance)

        # Check container exists
        out_caches = instance.data.get("outCache")

        root_container_data = instance.context.data.get("RootContainers")
        container = None
        if root_container_data:
            _geom = out_caches[0]

            for container_name, _data in root_container_data.items():
                geom_ns = lib.get_ns(_geom)
                if _data.get("namespace", "") in geom_ns:
                    container = container_name
                    break

        if not container:
            self.log.error("Get container failed. {}".format(_skip_msg))
            raise Exception("Get container failed: {}".format(instance))

        # Check asset exists
        asset_data = self._check_asset_exists(container)
        if not asset_data:
            raise Exception("Can't found asset: {} in this show.".format(
                container))

        asset_id = asset_data['_id']
        self.parent_asset_name = asset_data.get('name', '')
        instance.data["asset_name"] = self.parent_asset_name
        instance.data["asset_id"] = asset_id

        # Create children pointcache instance
        geometry_path = instance.data["geometry_path"]
        self._get_child_subset(instance, geometry_path, out_caches)

    def _get_child_subset(self, instance, geometry_path, out_caches):
        import maya.cmds as cmds

        # Get children
        children = cmds.listRelatives(geometry_path, children=True)
        children = [g for g in children if cmds.getAttr("{}.v".format(g))]

        if len(children) == 1:
            return

        skip_parent = False
        invalid_grp = []
        for child_name in children:
            # Get asset name
            child_root_group = ""
            for _group in cmds.listRelatives(
                    child_name, allDescendents=True, type="transform"):
                if _group.endswith(":ROOT"):
                    child_root_group = _group
                    break
            if not child_root_group:
                invalid_grp.append(child_name)
                _msg = "{}: Missing \"ROOT\" in model hierarchy.".\
                    format(child_name)
                self.log.error(_msg)
                continue

            if not cmds.attributeQuery(
                    'AvalonID', node=child_root_group, exists=True):
                invalid_grp.append(child_name)
                _msg = "{}: Missing \"AvalonID\" attribute on ROOT group. ".\
                    format(child_name)
                self.log.error(_msg)
                continue

            asset_id = cmds.getAttr(
                "{}.AvalonID".format(child_root_group)).split(":")[0]

            _filter = {"type": "asset", "_id": avalon.io.ObjectId(asset_id)}
            asset_data = avalon.io.find_one(_filter)

            if not asset_data:
                invalid_grp.append(child_name)
                _msg = "{}: Cant get model's asset data from db.". \
                    format(child_name)
                self.log.error(_msg)
                continue

            child_asset_name = asset_data.get('name', '')

            if not skip_parent:
                if str(child_asset_name) == str(self.parent_asset_name):
                    skip_parent = True
                    continue

            # Get child cache
            child_cache = [cache for cache in out_caches if child_name in cache]

            # Get subset name
            subset_name = "pointcache.{}.{}".format(
                instance.data["subset"].replace("pointcache.", ""),
                child_name.split(":")[-2]
            )

            self.__create_child_instance(
                instance,
                subset_name=subset_name,
                asset_name=child_asset_name,
                asset_id=asset_id,
                caches=child_cache
            )

        if invalid_grp:
            raise Exception(
                "%s <Check children subset usd> Failed."
                "Please check your models are from publish." % instance
            )

    def __create_child_instance(self, instance, subset_name=None,
                               asset_id=None, asset_name=None, caches=None):
        # Create new instance
        context = instance.context
        backup = instance

        if not self.ins_exists(context, subset_name):
            _family = "reveries.pointcache.child.usd"
            parent_pointcache_name = instance.data["subset"]

            _instance = context.create_instance(subset_name)
            _instance.data.update(backup.data)

            _instance.data["family"] = _family
            _instance.data["families"] = []
            _instance.data["subset"] = subset_name

            _instance.data["asset_name"] = asset_name
            _instance.data["asset_id"] = asset_id
            _instance.data["outCache"] = caches
            _instance.data["subsetGroup"] = "USD"
            _instance.data["parent_pointcache_name"] = parent_pointcache_name

    def _check_asset_exists(self, container):
        import maya.cmds as cmds

        asset_id = cmds.getAttr('{}.assetId'.format(container))
        _filter = {"type": "asset", "_id": avalon.io.ObjectId(asset_id)}
        asset_data = avalon.io.find_one(_filter)

        return asset_data
