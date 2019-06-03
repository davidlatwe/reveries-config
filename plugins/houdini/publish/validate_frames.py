
import pyblish.api


class ValidateFrames(pyblish.api.InstancePlugin):
    """Validate all frames's output file path"""

    order = pyblish.api.ValidatorOrder + 0.1
    label = "Validate Frames"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
        "reveries.pointcache",
        "reveries.standin",
    ]

    def process(self, instance):
        import hou
        from reveries.houdini import lib

        collected_frames = instance.data.get("frameOutputs", [])

        start_frame = instance.data.get("startFrame", None)
        end_frame = instance.data.get("endFrame", None)
        step = instance.data.get("step", None)

        if start_frame is None:
            if collected_frames:
                raise Exception("Render frame changed, please restart.")

            self.log.info("No frame range data, skipping.")
            return

        ropnode = instance[0]
        output_parm = lib.get_output_parameter(ropnode)
        raw_output = output_parm.rawValue()

        for count, frame in enumerate(range(start_frame, end_frame, step)):
            output = hou.expandStringAtFrame(raw_output, frame)

            if collected_frames[count] != output:
                raise Exception("Render frame changed, please restart.")

        if count != len(collected_frames):
            raise Exception("Render frame changed, please restart.")
