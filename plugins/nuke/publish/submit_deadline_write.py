
import os
import json
import copy
import platform
import pyblish.api


class SubmitDeadlineWrite(pyblish.api.InstancePlugin):
    """Publish via rendering Nuke Write nodes on Deadline

    Submitting jobs per write(instance) to deadline.

    """

    order = pyblish.api.ExtractorOrder + 0.2
    hosts = ["nuke"]
    label = "Deadline Write"

    families = [
        "reveries.write",
    ]

    targets = ["deadline"]

    def process(self, instance):
        import reveries

        reveries_path = reveries.__file__

        instance.data["submitted"] = True

        context = instance.context

        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        # Context data

        username = context.data["user"]
        comment = context.data.get("comment", "")
        project = context.data["projectDoc"]
        asset = context.data["assetDoc"]["name"]

        fpath = context.data["currentMaking"]
        nuke_version = context.data["nukeVersion"]

        project_id = str(project["_id"])[-4:].upper()
        project_code = project["data"].get("codename") or project_id
        fname = os.path.basename(fpath)

        batch_name = "({projcode}): [{asset}] {filename}".format(
            projcode=project_code,
            asset=asset,
            filename=fname
        )

        # Instance data

        subset = instance.data["subset"]
        version = instance.data["versionNext"]

        write_node = instance[0]

        deadline_pool = instance.data["deadlinePool"]
        deadline_prio = instance.data["deadlinePriority"]
        deadline_group = instance.data.get("deadlineGroup")

        if instance.data["deadlineSuspendJob"]:
            init_state = "Suspended"
        else:
            init_state = "Active"

        frame_start = int(instance.data["startFrame"])
        frame_end = int(instance.data["endFrame"])
        frame_step = int(instance.data["byFrameStep"])
        frame_per_task = instance.data["deadlineFramesPerTask"]

        frames = "{start}-{end}x{step}".format(
            start=frame_start,
            end=frame_end,
            step=frame_step,
        )

        output_path_keys = dict()
        head, tail = os.path.split(instance.data["outputPath"])
        output_path_keys["OutputDirectory0"] = head
        output_path_keys["OutputFilename0"] = tail

        job_name = "{subset} v{version:0>3}".format(
            subset=subset,
            version=version,
        )

        # Assemble payload

        payload = {
            "JobInfo": {
                "Plugin": "Nuke",
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
            "PluginInfo": {
                # Input
                "SceneFile": fpath,

                "Views": "",  # We don't render by views
                "WriteNode": write_node,

                # Mandatory for Deadline
                "Version": nuke_version,
                "Threads": 0,
                "RamUse": 0,
                "NukeX": False,
                "BatchMode": True,
                "BatchModeIsMovie": False,
                "ContinueOnError": False,
                "RenderMode": "Use Scene Settings",
                "EnforceRenderOrder": False,
                "StackSize": 0,
                "UseGpu": False,
                "GpuOverride": 0,
                "PerformanceProfiler": False,
                "PerformanceProfilerDir": "",
                "ScriptJob": False,
                "ScriptFilename": "",
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
            "IdOnly": True
        }

        payload["JobInfo"].update(output_path_keys)

        # Environment

        environment = self.assemble_environment(instance)

        parsed_environment = {
            "EnvironmentKeyValue%d" % index: u"{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        }
        payload["JobInfo"].update(parsed_environment)

        self.log.info("Submitting.. %s" % write_node)
        self.log.info(json.dumps(
            payload, indent=4, sort_keys=True)
        )

        # Submit

        submitter = context.data["deadlineSubmitter"]
        index = submitter.add_job(payload)

        # Publish script

        payload = copy.deepcopy(payload)

        script_file = os.path.join(os.path.dirname(reveries_path),
                                   "scripts",
                                   "deadline_publish.py")
        # Clean up
        payload["JobInfo"].pop("Frames")
        payload["JobInfo"].pop("ChunkSize")
        # Update
        payload["JobInfo"].update({
            "Name": "|| Publish: " + payload["JobInfo"]["Name"],
            "JobDependencies": index,
            "InitialStatus": "Active",
        })
        payload["PluginInfo"].update({
            "ScriptJob": True,
            "ScriptFilename": script_file,
        })

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
            # "MAYA_MODULE_PATH",
            # "ARNOLD_PLUGIN_PATH",
        ]:
            environment[var] = os.getenv(var, "")

        return environment
