
import os
import pyblish.api
import reveries.pipeline
import reveries.maya.io as io
import reveries.maya.capsule as capsule

from maya import cmds


class ExtractPointCache(reveries.pipeline.ExtractionDelegator):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract PointCache"
    families = [
        "reveries.animation",
        "reveries.pointcache",
    ]

    start_frame = 0
    end_frame = 0

    def extract(self, instance):
        cache_format = instance.data.get("format", "None")
        name = instance.data["subset"]

        context_data = instance.context.data
        self.start_frame = context_data.get("startFrame")
        self.end_frame = context_data.get("endFrame")

        extractor = getattr(self, "extract_" + cache_format, None)
        if extractor is None:
            msg = "Cache format {!r} not supported."
            raise TypeError(msg.format(cache_format))

        self.log.info("Exporting {0} of {1}...".format(cache_format, name))

        dirname = self.get_staging_dir(instance, cache_format)
        fname = name + ".{}"
        out_path = os.path.join(dirname, fname)

        with capsule.no_refresh(with_undo=True):
            with capsule.evaluation("off"):
                out_geo = instance.data.get("out_animation", instance[:])
                cmds.select(out_geo, replace=True, noExpand=True)
                instance.data["files"].append(extractor(out_path))

    def delegate(self, instance):
        cache_format = instance.data.get("format")
        name = instance.data["subset"]
        fname = name + ".{}"

        # for debug, give a fake path
        instance.data["stagingDir"] = os.path.join("on", "delegating")
        # `PENDING_SUFFIX` is a keyword for Loader
        fake_name = fname + reveries.pipeline.PENDING_SUFFIX

        if cache_format == "Alembic" or cache_format == "GPUCache":
            fake_name = fake_name.format("abc")
        elif cache_format == "FBXCache":
            fake_name = fake_name.format("fbx")
        else:
            msg = "Cache format {!r} not supported."
            raise TypeError(msg.format(cache_format))

        instance.data["files"].append(fake_name)

    def get_staging_dir(self, instance, cache_format):
        if cache_format == "FBXCache":
            # FBX GeoCache can not export to stagingDir, because the
            # exporter write the absolute path of cacheDir _fpc inside
            # .fbx
            dirname = instance.data["publish_dir"]
            if not os.path.isdir:
                os.makedirs(dirname)
        else:
            dirname = reveries.pipeline.temp_dir()
        instance.data["stagingDir"] = dirname
        return dirname

    def extract_Alembic(self, out_path):
        out_path = out_path.format("abc")
        io.export_alembic(out_path, self.start_frame, self.end_frame)
        return os.path.basename(out_path)

    def extract_FBXCache(self, out_path):
        out_path = out_path.format("fbx")
        io.export_fbx_set_pointcache("ReveriesCache")
        io.export_fbx(out_path)
        return os.path.basename(out_path)

    def extract_GPUCache(self, out_path):
        out_path = out_path.format("abc")
        io.export_gpu(out_path, self.start_frame, self.end_frame)
        return os.path.basename(out_path)
