
import pyblish.api
from reveries.maya import utils as maya_utils
from reveries.maya import pipeline
from reveries import utils


class ValidateRenderSettings(pyblish.api.InstancePlugin):
    """Ensure render setttings has been set correctly

        This plugin validate the following settings:
            * file name prefix
            * file name extension
            * rendering range (strict)
            * render resolution

    """

    label = "Render Settings"
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]
    families = [
        "reveries.imgseq.render",
        "reveries.imgseq.lookdev",
    ]

    extensions = ("exr", "png")

    @classmethod
    def get_invalid_range(cls, instance):
        """Rendering range should be the same as pre-defined range"""
        project = instance.context.data["projectDoc"]
        asset_name = pipeline.has_turntable()
        proj_start, proj_end, _ = utils.compose_timeline_data(project,
                                                              asset_name)
        render_start = instance.data["startFrame"]
        render_end = instance.data["endFrame"]

        if proj_start != render_start or proj_end != render_end:
            cls.log.error("Rendering frame range is not correct.")
            cls.log.error("start and end frame should be {0} - {1}."
                          "".format(proj_start, proj_end))
            return True

    @classmethod
    def get_invalid_resolution(cls, instance):
        """Rendering resolution should be the same as project settings"""
        project = instance.context.data["projectDoc"]
        proj_width, proj_height = utils.get_resolution_data(project)

        layer = instance.data["renderlayer"]
        scene_width, scene_height = maya_utils.get_render_resolution(layer)

        if proj_width != scene_width or proj_height != scene_height:
            cls.log.error("Rendering resolution is not correct.")
            cls.log.error("Resolution width and height should be {0} x {1}."
                          "".format(proj_width, proj_height))
            return True

    @classmethod
    def get_invalid_fileprefix(cls, instance):
        """filename prefix must set and have tags"""
        prefix = instance.data["fileNamePrefix"] or ""
        cls.log.debug("Collected file name prefix: %s" % prefix)

        has_invalid = False

        if not prefix:
            has_invalid = True
            cls.log.error("File name prefix must set.")

        if "<Scene>" not in prefix:
            has_invalid = True
            cls.log.error("File name prefix must contain <Scene> tag.")

        has_renderlayer = instance.context.data["hasRenderLayers"]
        if has_renderlayer:
            tags = (["<Layer>", "<layer>", "%l"] if "vray" else
                    ["<RenderLayer>", "<Layer>", "%l"])

            if not any(t in prefix for t in tags):
                has_invalid = True
                cls.log.error("File name prefix must contain renderlayer "
                              "tag since the scene has renderlayers.")

        return has_invalid

    @classmethod
    def get_invalid_ext(cls, instance):
        layer = instance.data["renderlayer"]
        filename = maya_utils.compose_render_filename(layer)
        cls.log.debug("Composed file name: %s" % filename)

        ext = filename.rsplit(".", 1)[-1]

        if ext not in cls.extensions:
            cls.log.error("File extension should be set to one of {}."
                          "".format(cls.extensions))
            return True

    def process(self, instance):

        has_invalid = False

        self.log.info("Validating frame range..")
        if self.get_invalid_range(instance):
            has_invalid = True

        self.log.info("Validating image resolution..")
        if self.get_invalid_resolution(instance):
            has_invalid = True

        self.log.info("Validating filename prefix..")
        if self.get_invalid_fileprefix(instance):
            has_invalid = True

        self.log.info("Validating file extension..")
        if self.get_invalid_ext(instance):
            has_invalid = True

        # (TODO) validate animation enabled or not (single frame)
        #        validate output path
        outputs = instance.data["outputPaths"]
        for aov, path in outputs.items():
            self.log.debug("AOV: %s" % aov)
            self.log.debug("    %s" % path)

        if has_invalid:
            raise Exception("Render settings validation failed.")

    @classmethod
    def fix_invalid_range(cls, instance):
        NotImplemented

    @classmethod
    def fix_invalid_resolution(cls, instance):
        NotImplemented

    @classmethod
    def fix_invalid_fileprefix(cls, instance):
        NotImplemented

    @classmethod
    def fix_invalid_ext(cls, instance):
        NotImplemented
