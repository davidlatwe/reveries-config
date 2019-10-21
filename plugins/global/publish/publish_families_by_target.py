
import pyblish.api


class PublishFamiliesByTarget(pyblish.api.ContextPlugin):
    """建立與發佈目標 (Target) 相應的家族 (Family) 清單"""

    """Listing publish target supported families
    """

    order = pyblish.api.CollectorOrder - 0.4
    label = "Families 支援清單"

    ALL_FAMILIES = set([
        "reveries.shotpkg",
        "reveries.imgseq",
        "reveries.imgseq.playblast",
        "reveries.imgseq.render",
        "reveries.model",
        "reveries.xgen",
        "reveries.xgen.legacy",
        "reveries.xgen.interactive",
        "reveries.rig",
        "reveries.look",
        "reveries.texture",
        "reveries.setdress",
        "reveries.animation",
        "reveries.pointcache",
        "reveries.camera",
        "reveries.lightset",
        "reveries.standin",
        "reveries.atomscrowd",
        "reveries.mayashare",
        "reveries.vdbcache",
    ])

    families_by_target = {

        "default": [],

        "localhost": [
            family for family in ALL_FAMILIES if family not in [
                # Exclusion
                "reveries.imgseq.render",
            ]
        ],

        "deadline": [
            "reveries.pointcache",
            "reveries.standin",
            "reveries.imgseq",
            "reveries.imgseq.playblast",
            "reveries.imgseq.render",
        ],

    }

    def process(self, context):

        targeted = set()

        for target in pyblish.api.registered_targets():
            self.log.info(target)
            targeted.update(self.families_by_target[target])

        context.data["targetFamilies"] = targeted or self.ALL_FAMILIES
