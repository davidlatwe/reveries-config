
import os
import json
import copy
import platform
import pyblish.api


class SubmitDeadlinePublish(pyblish.api.ContextPlugin):
    """Publish via running script on Deadline

    Submitting jobs per instance group to deadline.

    """

    order = pyblish.api.ExtractorOrder + 0.3
    hosts = ["houdini"]
    label = "Deadline Publish"

    targets = ["deadline"]

    def process(self, context):
        import reveries

        reveries_path = reveries.__file__
        script_file = os.path.join(os.path.dirname(reveries_path),
                                   "scripts",
                                   "deadline_publish.py")

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

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            if instance.data.get("isDependency", False):
                continue

            if instance.data.get("submitted", False):
                continue

            subset = instance.data["subset"]
            version = instance.data["versionNext"]

            deadline_pool = instance.data["deadlinePool"]  # Camera does not have this
            deadline_prio = instance.data["deadlinePriority"]
            deadline_group = instance.data.get("deadlineGroup")

            job_name = "{subset} v{version:0>3}".format(
                subset=subset,
                version=version,
            )

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
                    "OutputDriver": "",
                    # Output Filename
                    "Output": "",

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
                "OutputDriver": "/out/deadline_publish_script",
            })

            submitter.add_job(payload)

    def assemble_environment(self, instance):
        """Compose submission required environment variables for instance

        Return:
            environment (dict): A set of remote variables, return `None` if
                instance is not assigning to remote site or publish is
                disabled.

        """
        submitter = instance.context.data["deadlineSubmitter"]
        environment = submitter.instance_env(instance)

        return environment
