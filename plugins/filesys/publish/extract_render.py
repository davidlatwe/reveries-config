
import os
import pyblish.api


class ExtractRender(pyblish.api.InstancePlugin):

    label = "Extract Render"
    order = pyblish.api.ExtractorOrder
    hosts = ["filesys"]

    families = [
        "reveries.renderlayer",
    ]

    def process(self, instance):

        staging_dir = instance.data["stagingDir"]

        sequence_data = instance.data["sequences"]
        is_stereo = instance.data["isStereo"]

        sequence = dict()
        patterns = list()
        start = None
        end = None
        for aov_name, data in sequence_data.items():
            start = data["start"] if start is None else min(start, data["start"])
            end = data["end"] if end is None else max(end, data["end"])

            pattern = data["fpattern"]

            sequence[aov_name] = {
                "imageFormat": os.path.splitext(pattern)[-1],
                "fpattern": pattern,
            }

            if is_stereo:
                patterns.append(pattern.format(stereo="Left"))
                patterns.append(pattern.format(stereo="Right"))
            else:
                patterns.append(pattern)

        hardlinks = list()
        missing = False
        for fname in patterns:
            for frame_num in range(start, end + 1):
                full_path = os.path.join(staging_dir, fname % frame_num)
                if os.path.isfile(full_path):
                    hardlinks.append(fname % frame_num)
                else:
                    print("%s not exists, skip." % full_path)
                    missing = True

        if missing:
            self.log.warning("Some files missing, sequence may incomplete. "
                             "See log..")

        if not hardlinks:
            raise Exception("No file to extract, operation failed.")

        instance.data["startFrame"] = start
        instance.data["endFrame"] = end

        instance.data["repr.renderLayer.sequence"] = sequence
        instance.data["repr.renderLayer.stereo"] = is_stereo

        instance.data["repr.renderLayer._stage"] = staging_dir
        instance.data["repr.renderLayer._hardlinks"] = hardlinks
