
import os
import json
import platform
import pyblish.api
import reveries


class SubmitDeadlinePublish(pyblish.api.ContextPlugin):
    """Publish via running script on Deadline

    Submitting jobs per instance group to deadline.

    """

    order = pyblish.api.ExtractorOrder + 0.492
    hosts = ["maya"]
    label = "Deadline Publish"

    targets = ["deadline"]

    RENDER_TYPES = [
        "reveries.renderlayer",
    ]

    def process(self, context):
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        # Context data

        username = context.data["user"]
        comment = context.data.get("comment", "")
        project = context.data["projectDoc"]
        asset = context.data["assetDoc"]["name"]

        fpath = context.data["currentMaking"]
        workspace = context.data["workspaceDir"]
        maya_version = context.data["mayaVersion"]

        project_id = str(project["_id"])[-4:].upper()
        project_code = project["data"].get("codename") or project_id
        fname = os.path.basename(fpath)

        batch_name = "({projcode}): [{asset}] {filename}".format(
            projcode=project_code,
            asset=asset,
            filename=fname
        )

        # Instance data

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            if not instance.data.get("dumpedExtractors"):
                continue

            subset = instance.data["subset"]
            version = instance.data["versionNext"]

            deadline_pool = instance.data["deadlinePool"]
            deadline_prio = instance.data["deadlinePriority"]
            deadline_group = instance.data.get("deadlineGroup")

            frame_per_task = instance.data.get("deadlineFramesPerTask", 1)

            try:
                frame_start = int(instance.data["startFrame"])
                frame_end = int(instance.data["endFrame"])
                frame_step = int(instance.data["byFrameStep"])

            except KeyError:
                frames = None
            else:
                frames = "{start}-{end}x{step}".format(
                    start=frame_start,
                    end=frame_end,
                    step=frame_step,
                )

            job_name = "{subset} v{version:0>3}".format(
                subset=subset,
                version=version,
            )

            if instance.data.get("deadlineSuspendJob", False):
                init_state = "Suspended"
            else:
                init_state = "Active"

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
                    "Group": deadline_group,
                    "Priority": deadline_prio,

                    "Frames": frames,
                    "ChunkSize": frame_per_task,
                    "InitialStatus": init_state,

                    "ExtraInfo0": project["name"],
                },

                # Mandatory for Deadline, may be empty
                "AuxFiles": [],
                "IdOnly": True
            }

            if instance.data.get("hasYeti"):
                # Change Deadline group for Yeti
                payload["JobInfo"]["Group"] = "yeti_render"

            if instance.data["family"] in self.RENDER_TYPES:
                # Render Job
                output_dir = context.data["outputDir"]
                has_renderlayer = context.data["hasRenderLayers"]
                use_rendersetup = context.data["usingRenderSetup"]

                output_prefix = instance.data["fileNamePrefix"]
                renderlayer = instance.data["renderlayer"]
                renderer = instance.data["renderer"]
                rendercam = instance.data["camera"]

                payload["PluginInfo"] = {
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
            else:
                # Script Job
                reveries_path = reveries.__file__
                script_file = os.path.join(os.path.dirname(reveries_path),
                                           "scripts",
                                           "deadline_extract.py")

                payload["PluginInfo"] = {
                    "ScriptJob": True,
                    "ScriptFilename": script_file,
                    # Input
                    "SceneFile": fpath,
                    # Resolve relative references
                    "ProjectPath": workspace,
                    # Mandatory for Deadline
                    "Version": maya_version,
                }

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
                "EnvironmentKeyValue%d" % index: u"{key}={value}".format(
                    key=key,
                    value=environment[key]
                ) for index, key in enumerate(environment)
            }
            payload["JobInfo"].update(parsed_environment)

            self.log.info("Submitting.. %s" % instance)
            self.log.info(json.dumps(
                payload, indent=4, sort_keys=True)
            )

            # Submit

            submitter = context.data["deadlineSubmitter"]
            index = submitter.add_job(payload)

            dump_path = instance.data["dumpPath"]
            submitter.append_filesys_publish(payload, index, dump_path)

    def assemble_environment(self, instance):
        """Compose submission required environment variables for instance

        Return:
            environment (dict): A set of remote variables, return `None` if
                instance is not assigning to remote site or publish is
                disabled.

        """
        submitter = instance.context.data["deadlineSubmitter"]
        environment = submitter.environment()

        # From current environment
        for var in [
            "MAYA_MODULE_PATH",
            "ARNOLD_PLUGIN_PATH",
        ]:
            environment[var] = os.getenv(var, "")

        dumped = ";".join(instance.data["dumpedExtractors"])
        environment["PYBLISH_EXTRACTOR_DUMPS"] = dumped

        return environment
