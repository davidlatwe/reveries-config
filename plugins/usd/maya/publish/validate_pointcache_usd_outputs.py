import avalon

import pyblish.api


class ValidatePointCacheUSDOutputs(pyblish.api.InstancePlugin):
    """Validate asset already published usd."""

    order = pyblish.api.ValidatorOrder + 0.492

    label = "Validate PointCache USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache.usd",
        "reveries.pointcache.child.usd"
    ]

    def process(self, instance):
        from reveries.maya.usd import get_export_hierarchy

        if instance.data.get("isDummy"):
            return

        self.out_cache = instance.data.get("outCache")

        # Check MOD group long name
        export_node, root_usd_path = get_export_hierarchy(self.out_cache[0])
        if not export_node or not root_usd_path:
            raise Exception("Can't get correct model hierarchy, "
                            "please check with TD.")

        # r'|..|..|HanMaleA_rig_02:HanMaleA_model_01_:Geometry'
        instance.data["export_node"] = export_node
        # r'/rigDefault/ROOT/Group/Geometry/modelDefault/ROOT'
        instance.data["root_usd_path"] = root_usd_path

    # def _check_export_hierarchy(self, geom):
    #     import maya.cmds as cmds
    #
    #     cmds.listRelatives(geom, allDescendents=True)
    #     geom_long = cmds.ls(geom, long=True)
    #     if not geom_long:
    #         return '', ''
    #     parents = geom_long[0].split("|")[1:-1]
    #     parents_long_named = ["|".join(parents[:i])
    #                           for i in xrange(1, 1 + len(parents))]
    #     export_node = [_p for _p in parents_long_named
    #                    if _p.endswith(':Geometry')]  # MOD
    #
    #     # Get mod root path
    #     root_usd_path = ''
    #     parents_without_ns = [parents[i].split(':')[-1]
    #                           for i in xrange(0, len(parents))]
    #     for item in ["|".join(parents_without_ns[:i])
    #                  for i in xrange(1, 1 + len(parents_without_ns))]:
    #         # if item.endswith('MOD'):
    #         if item.endswith('ROOT') and item.split('|')[-2] != 'rigDefault':
    #             root_usd_path = '|{}'.format(item).\
    #                 replace('|MOD', '').replace('|', '/')
    #
    #     return export_node[0] if export_node else '', root_usd_path
