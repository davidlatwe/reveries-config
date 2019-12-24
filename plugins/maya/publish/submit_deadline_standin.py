
import os
import platform
import copy
import json
import pyblish.api


class SubmitDeadlineStandIn(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.2
    hosts = ["maya"]
    label = "Deadline Stand-In"

    families = [
        "reveries.standin",
    ]

    targets = ["deadline"]

    def process(self, instance):
        import reveries

        reveries_path = reveries.__file__
        script_file = os.path.join(os.path.dirname(reveries_path),
                                   "scripts",
                                   "deadline_standin_by_frame.py")

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
        deadline_prior = instance.data["deadlinePriority"]

        frame_start = int(instance.data["startFrame"])
        frame_end = int(instance.data["endFrame"])
        frame_step = int(instance.data["byFrameStep"])

        frames = "{start}-{end}x{step}".format(
            start=frame_start,
            end=frame_end,
            step=frame_step,
        )

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
                "ChunkSize": 1,

                "ExtraInfo0": project["name"],
            },
            "PluginInfo": {

                "ScriptJob": True,
                "ScriptFilename": script_file,

                # Input
                "SceneFile": fpath,
                # Resolve relative references
                "ProjectPath": workspace,
                # Mandatory for Deadline
                "Version": maya_version,
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
            "IdOnly": True
        }

        if instance.data.get("hasYeti"):
            # Change Deadline group for Yeti
            payload["JobInfo"]["Group"] = "yeti_render"

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
            "MAYA_MODULE_PATH",
            "ARNOLD_PLUGIN_PATH",
        ]:
            environment[var] = os.getenv(var, "")

        # Remote data json file path
        environment["REMOTE_DATA_PATH"] = instance.data["remoteDataPath"]

        return environment
