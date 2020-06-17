
import os
import pyblish.api


class RemoveOutdatedProgress(pyblish.api.InstancePlugin):
    """Remove previous integrated progress outputs"""

    label = "Remove Outdated Progress"
    order = pyblish.api.ExtractorOrder - 0.41
    hosts = ["filesys"]

    def process(self, instance):
        repr_dirs = self.parse_src_dst_dirs(instance)
        progress = instance.data.get("_progressiveOutput")

        outdated = list()
        not_matched = list()

        for file in progress:
            file = file.replace("\\", "/")
            for _, (src, dst) in repr_dirs.items():
                if not file.startswith(src):
                    continue

                tail = os.path.relpath(file, src)
                outdated.append(os.path.join(dst, tail).replace("\\", "/"))
                break

            else:
                not_matched.append(file)

        if not_matched:
            self.log.error("! " * 30)
            for repr_name, (src, _) in repr_dirs.items():
                self.log.error("    [%s] - %s" % (repr_name, src))
            self.log.error("The following files did not match with any "
                           "of above stage dirs:")
            for file in not_matched:
                self.log.error("    %s" % file)

            raise FileNotFoundError("Progress output file not matched.")

        for file in outdated:
            if os.path.isfile(file):
                try:
                    os.remove(file)
                except Exception as e:
                    self.log.error("Failed to remove: %s" % file)
                    raise e

    def parse_src_dst_dirs(self, instance):

        repr_dirs = dict()

        template_publish = instance.data["publishPathTemplate"]
        template_data = instance.data["publishPathTemplateData"]

        for key in sorted(instance.data.keys()):
            if not key.startswith("repr."):
                continue

            _, repr_name, _ = key.split(".", 2)

            if repr_name.startswith("_"):
                continue

            if repr_name not in repr_dirs:

                src = instance.data["repr.%s._stage" % repr_name]
                dst = template_publish.format(representation=repr_name,
                                              **template_data)

                repr_dirs[repr_name] = (src.replace("\\", "/"),
                                        dst.replace("\\", "/"))

        return repr_dirs
