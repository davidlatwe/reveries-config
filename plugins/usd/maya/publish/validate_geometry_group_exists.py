import avalon

import pyblish.api


class ValidateGeometryExists(pyblish.api.InstancePlugin):
    """Validate geometry group in hierarchy."""

    # order = pyblish.api.ValidatorOrder + 0.49
    order = pyblish.api.CollectorOrder + 0.4991

    label = "Validate Geometry Exists"
    hosts = ["maya"]
    families = [
        "reveries.pointcache.usd"
    ]

    def process(self, instance):
        import maya.cmds as cmds

        if instance.data.get("isDummy"):
            return

        out_caches = instance.data.get("outCache")

        if out_caches:
            geom = out_caches[0]

            cmds.listRelatives(geom, allDescendents=True)
            geom_long = cmds.ls(geom, long=True)
            if not geom_long:
                return
            parents = geom_long[0].split("|")[1:-1]
            parents_long_named = ["|".join(parents[:i])
                                  for i in xrange(1, 1 + len(parents))]

            for _path in parents_long_named:
                if _path.endswith(':Geometry'):
                    instance.data["geometry_path"] = _path
                    break

        if not instance.data.get("geometry_path", ""):
            self.log.error(
                "Missing geometry group in rig hierarchy."
                "Please turn off \"exportAniUSDData\" to skip USD publish."
            )
            raise Exception("%s <Geometry Group Check> Failed." % instance)
