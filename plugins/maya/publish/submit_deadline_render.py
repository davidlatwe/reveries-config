
import os
import json
import platform
import pyblish.api
from reveries.maya import utils


class SubmitDeadlineRender(pyblish.api.InstancePlugin):
    """Publish via rendering Maya renderlayers on Deadline

    Submitting jobs per renderlayer(instance) to deadline.

    """

    order = pyblish.api.ExtractorOrder + 0.2
    hosts = ["maya"]
    label = "Deadline Render"

    families = [
        "reveries.imgseq.render",
    ]

    targets = ["deadline"]

    def process(self, instance):

        instance.data["submitted"] = True

        context = instance.context

        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        # Context data

        username = context.data["user"]
        comment = context.data.get("comment", "")
        project = context.data["projectDoc"]
        asset = context.data["assetDoc"]["name"]

        fpath = context.data["currentMaking"]
        workspace = context.data["workspaceDir"]
        maya_version = context.data["mayaVersion"]

        output_dir = context.data["outputDir"].replace("\\", "/")
        has_renderlayer = context.data["hasRenderLayers"]
        use_rendersetup = context.data["usingRenderSetup"]

        project_id = str(project["_id"])[-4:].upper()
        project_code = project["data"].get("codename", project_id)
        fname = os.path.basename(fpath)

        batch_name = "({projcode}): [{asset}] {filename}".format(
            projcode=project_code,
            asset=asset,
            filename=fname
        )

        # Instance data

        subset = instance.data["subset"]
        version = instance.data["versionNext"]

        output_prefix = instance.data["fileNamePrefix"]
        renderlayer = instance.data["renderlayer"]
        renderer = instance.data["renderer"]
        rendercam = instance.data["renderCam"][0]

        deadline_pool = instance.data["deadlinePool"]
        deadline_prior = instance.data["deadlinePriority"]

        frame_start = int(instance.data["startFrame"])
        frame_end = int(instance.data["endFrame"])
        frame_step = int(instance.data["byFrameStep"])
        frame_per_task = instance.data["deadlineFramesPerTask"]

        frames = "{start}-{end}x{step}".format(
            start=frame_start,
            end=frame_end,
            step=frame_step,
        )

        # (NOTE) This takes long time to process
        output_paths = utils.get_output_paths(output_dir,
                                              renderer,
                                              renderlayer,
                                              rendercam)
        output_path_keys = dict()
        for count, outpath in enumerate(output_paths.values()):
            head, tail = os.path.split(outpath)
            output_path_keys["OutputDirectory%d" % count] = head
            output_path_keys["OutputFilename%d" % count] = tail

        job_name = "{subset} v{version:0>3}".format(
            subset=subset,
            version=version,
        )

        # Assemble payload

        payload = {
            "JobInfo": {
                "Plugin": "MayaBatch",
                "BatchName": batch_name,  # Top-level group name
                "Name": job_name,
                "UserName": username,
                "MachineName": platform.node(),
                "Comment": comment,
                "Pool": deadline_pool,
                # "Group": deadline_group,
                "Priority": deadline_prior,
                "Frames": frames,
                "ChunkSize": frame_per_task,

                "ExtraInfo0": project["name"],
            },
            "PluginInfo": {
                # Input
                "SceneFile": fpath,
                # Resolve relative references
                "ProjectPath": workspace,
                # Mandatory for Deadline
                "Version": maya_version,
                # Output directory and filename
                "OutputFilePath": output_dir,
                "OutputFilePrefix": output_prefix,

                "UsingRenderLayers": has_renderlayer,
                "UseLegacyRenderLayers": not use_rendersetup,
                "RenderLayer": renderlayer,
                "Renderer": renderer,
                "Camera": rendercam,
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
            "IdOnly": True
        }

        payload["JobInfo"].update(output_path_keys)

        # Environment

        environment = self.assemble_environment(instance)

        if instance.data.get("hasAtomsCrowds"):
            # Change Deadline group for AtomsCrowd
            payload["JobInfo"]["Group"] = "atomscrowd"
        else:
            # AtomsCrowd module path is available for every machine by
            # default, so we must remove it if this renderLayer does
            # not require AtomsCrowd plugin. Or the license will not
            # be enough for other job that require Atoms.
            module_path = environment["MAYA_MODULE_PATH"]
            filtered = list()
            for path in module_path.split(";"):
                if "AtomsMaya" not in path:
                    filtered.append(path)
            environment["MAYA_MODULE_PATH"] = ";".join(filtered)

        parsed_environment = {
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        }
        payload["JobInfo"].update(parsed_environment)

        self.log.info("Submitting.. %s" % renderlayer)
        self.log.info(json.dumps(
            payload, indent=4, sort_keys=True)
        )

        # Submit

        submitter = context.data["deadlineSubmitter"]
        submitter.add_job(payload)

    def assemble_environment(self, instance):
        """Compose submission required environment variables for instance

        Return:
            environment (dict)

        """
        submitter = instance.context.data["deadlineSubmitter"]
        environment = submitter.instance_env(instance)

        # From current environment
        for var in [
            "MAYA_MODULE_PATH",
            "ARNOLD_PLUGIN_PATH",
        ]:
            environment[var] = os.getenv(var, "")

        return environment
