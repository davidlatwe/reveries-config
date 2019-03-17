
import pyblish.api
from avalon import io
from reveries.maya import utils as maya_utils
from reveries.maya import pipeline
from reveries import utils


class ValidateRenderResolution(pyblish.api.InstancePlugin):
    """Ensure render setttings has been set correctly

        This plugin validate the render resolution

    """

    label = "Render Resolution"
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    families = [
        "reveries.imgseq.render",
    ]

    @classmethod
    def get_invalid(cls, instance):
        """Rendering resolution should be the same as project settings"""
        valid_resolutions = list()

        project = instance.context.data["projectDoc"]
        is_turntable = pipeline.has_turntable()

        turntable = project["data"]["pipeline"]["maya"].get("turntable")
        if turntable is not None and turntable == is_turntable:
            # (NOTE) When publishing turntable, some asset may need other
            #        render resolution width/height to fit in.
            #
            #        To add extra valid resolution for asset, add this to
            #        the turntable asset data:
            #
            #           "exceptions" : {
            #               "assetName": [
            #                   [width1, height1],
            #                   [width2, height2],
            #                   ...
            #                ]
            #            }
            #
            # (TODO) Might need to think a better way to implement this.
            #
            ttable_doc = io.find_one({"type": "asset",
                                      "name": turntable})
            ttable_data = ttable_doc["data"]
            exception = ttable_data["exceptions"].get(instance.data["asset"])
            if exception is not None:
                valid_resolutions += exception.get("resolution", [])

        proj_width, proj_height = utils.get_resolution_data(project,
                                                            is_turntable)
        valid_resolutions.append((proj_width, proj_height))

        layer = instance.data["renderlayer"]
        scene_width, scene_height = maya_utils.get_render_resolution(layer)

        invalid = True
        for res in valid_resolutions:
            if res[0] == scene_width or res[1] == scene_height:
                invalid = False
                break

        if invalid:
            cls.log.error("Resolution width and height should be {0} x {1}."
                          "".format(valid_resolutions.pop()))
            for res in valid_resolutions:
                cls.log.error("Or {0} x {1}".format(res))
        return invalid

    def process(self, instance):
        self.log.info("Validating image resolution..")
        if self.get_invalid(instance):
            raise Exception("Rendering resolution is not correct.")

    @classmethod
    def fix_invalid(cls, instance):
        NotImplemented
