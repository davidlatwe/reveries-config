
import os
import pyblish.api


class ExtractWrite(pyblish.api.InstancePlugin):
    """Start GUI rendering if not delegate to Deadline
    """

    label = "Extract Write"
    order = pyblish.api.ExtractorOrder
    hosts = ["nuke"]
    families = [
        "reveries.write",
    ]

    def process(self, instance):
        """Extract per renderlayer that has AOVs (Arbitrary Output Variable)
        """
        import nukescripts

        node = instance[0]

        staging_path = instance.data["outputPath"]
        staging_dir, pattern = os.path.split(staging_path)
        published_dir = self.published_dir(instance)

        if not os.path.isdir(staging_dir):
            os.makedirs(staging_dir)

        sequence = dict()
        files = list()

        sequence["_"] = {
            "imageFormat": instance.data["fileExt"],
            "fpattern": pattern,
            "resolution": instance.context.data["resolution"],
        }

        start = instance.data["startFrame"]
        end = instance.data["endFrame"]
        step = instance.data["step"]

        fname = nukescripts.frame.replaceHashes(pattern)
        for frame_num in range(start, end, step):
            files.apppend(fname % frame_num)

        seq_pattern = os.path.join(published_dir, pattern).replace("\\", "/")
        instance.data["publishedSeqPatternPath"] = seq_pattern

        instance.data["repr.imageSeq._stage"] = staging_dir
        instance.data["repr.imageSeq._hardlinks"] = files
        instance.data["repr.imageSeq.sequence"] = sequence
        instance.data["repr.imageSeq._delayRun"] = {
            "func": self.render,
            "args": [
                node.fullName(),
                start, end, step,
            ],
        }

    def published_dir(self, instance):
        template_publish = instance.data["publishPathTemplate"]
        template_data = instance.data["publishPathTemplateData"]
        published_dir = template_publish.format(representation="TexturePack",
                                                **template_data)
        return published_dir

    def render(self, node, start, end, step):
        import nuke

        nuke.render(node,
                    start=start,
                    end=end,
                    incr=step)
