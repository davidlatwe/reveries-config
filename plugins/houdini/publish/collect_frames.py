
import pyblish.api


class CollectFrames(pyblish.api.InstancePlugin):
    """Collect all frames' output file path"""

    order = pyblish.api.CollectorOrder
    label = "Collect Frames"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
        "reveries.pointcache",
        "reveries.standin",
    ]

    def process(self, instance):
        import hou
        from reveries.houdini import lib

        start_frame = instance.data.get("startFrame", None)
        end_frame = instance.data.get("endFrame", None)
        step = instance.data.get("step", None)

        if start_frame is None:
            self.log.info("No frame range data, skipping.")
            return

        self.log.info("Collecting range: [{s} - {e} @ {p}]"
                      "".format(s=start_frame, e=end_frame, p=step))

        ropnode = instance[0]

        output_parm = lib.get_output_parameter(ropnode)
        raw_output = output_parm.rawValue()

        frames = list()
        for frame in range(start_frame, end_frame + 1, step):
            output = hou.expandStringAtFrame(raw_output, frame)
            frames.append(output)

        instance.data.update({"frameOutputs": frames})
