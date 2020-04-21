
import os
import json
import platform
import pyblish.api


class SubmitDeadlineRender(pyblish.api.InstancePlugin):
    """Publish via rendering rop node on Deadline

    Submitting jobs per instance to deadline.

    """

    order = pyblish.api.ExtractorOrder + 0.492
    hosts = ["houdini"]
    label = "Deadline Render"

    families = [
        "reveries.pointcache",
        "reveries.camera",
        "reveries.standin",
        "reveries.vdbcache",
    ]

    targets = ["deadline"]

    def process(self, instance):
        from reveries.houdini import lib

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
        houdini_version = context.data["houdiniVersion"]

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

        deadline_pool = instance.data["deadlinePool"]
        deadline_prio = instance.data["deadlinePriority"]
        deadline_group = instance.data.get("deadlineGroup")

        frame_per_task = instance.data.get("deadlineFramesPerTask", 1)

        try:
            frame_start = int(instance.data["startFrame"])
            frame_end = int(instance.data["endFrame"])
            frame_step = int(instance.data["step"])

        except KeyError:
            frames = None
        else:
            frames = "{start}-{end}x{step}".format(
                start=frame_start,
                end=frame_end,
                step=frame_step,
            )
            if instance.data["singleOutput"]:
                frame_per_task = len(range(frame_start, frame_end + 1))

        job_name = "{subset} v{version:0>3}".format(
            subset=subset,
            version=version,
        )

        if instance.data.get("deadlineSuspendJob", False):
            init_state = "Suspended"
        else:
            init_state = "Active"

        ropnode = instance[0]

        # Override output to use original $HIP
        output = lib.get_output_parameter(ropnode).rawValue()
        on_HIP = output.startswith("$HIP")
        origin_HIP = os.path.dirname(context.data["originMaking"])
        output = output.replace("$HIP", origin_HIP, 1) if on_HIP else None
        # (NOTE) ^^^ For a fixed staging dir
        #   We need this because the scene file we submit to Deadline is a
        #   backup under `$HIP/_published` dir which copied via extractor
        #   plugin `AvalonSaveScene`.
        #
        #   Note that the Deadline (10.0.27.2) Houdini plugin does not support
        #   output filename override if the ROP node type is `alembic`. So to
        #   make this work, I have modified the Deadline Houdini plugin script
        #   `{DeadlineRepo}/plugins/Houdini/hrender_dl.py` at line 375:
        #   ```diff
        #   - elif ropType == "rop_alembic":
        #   + elif ropType in ("rop_alembic", "alembic"):
        #   ```

        # Assemble payload

        payload = {
            "JobInfo": {
                "Plugin": "Houdini",
                "BatchName": batch_name,  # Top-level group name
                "Name": job_name,
                "UserName": username,
                "MachineName": platform.node(),
                "Comment": comment,
                "Pool": deadline_pool,
                "Priority": deadline_prio,
                "Group": deadline_group,

                "Frames": frames,
                "ChunkSize": frame_per_task,
                "InitialStatus": init_state,

                "ExtraInfo0": project["name"],
            },
            "PluginInfo": {

                "SceneFile": fpath,
                "Build": "64bit",
                "Version": houdini_version,

                # Renderer Node
                "OutputDriver": ropnode.path(),
                # Output Filename
                "Output": output,

                "IgnoreInputs": False,
                "GPUsPerTask": 0,
                "SelectGPUDevices": "",
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
            "IdOnly": True
        }

        # Environment

        environment = self.assemble_environment(instance)

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
        submitter.add_job(payload)

    def assemble_environment(self, instance):
        """Compose submission required environment variables for instance

        Return:
            environment (dict): A set of remote variables, return `None` if
                instance is not assigning to remote site or publish is
                disabled.

        """
        submitter = instance.context.data["deadlineSubmitter"]
        environment = submitter.environment()

        optional_vars = [
            "AVALON_CACHE_ROOT",
            "JOB",
        ]
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                environment[var] = value

        dumped = ";".join(instance.data["dumpedExtractors"])
        environment["PYBLISH_EXTRACTOR_DUMPS"] = dumped

        environment["PYBLISH_DUMP_FILE"] = instance.data["dumpPath"]

        return environment
