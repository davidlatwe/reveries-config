
import os
import json
import platform
import pyblish.api


class SubmitDeadlinePublish(pyblish.api.ContextPlugin):
    """Publish via running script on Deadline

    Submitting jobs per instance group to deadline.

    """

    order = pyblish.api.ExtractorOrder + 0.3
    hosts = ["maya"]
    label = "Deadline Publish"

    targets = ["deadline"]

    def process(self, context):
        import reveries

        reveries_path = reveries.__file__
        script_file = os.path.join(os.path.dirname(reveries_path),
                                   "scripts",
                                   "deadline_publish.py")

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
        project_code = project["data"].get("codename", project_id)
        fname = os.path.basename(fpath)

        batch_name = "({projcode}): [{asset}] {filename}".format(
            projcode=project_code,
            asset=asset,
            filename=fname
        )

        deadline = project["data"]["deadline"]["maya"]

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

            deadline_pool = instance.data.get("deadlinePool",
                                              deadline["defaultPool"])

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
                    "Priority": 100,

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
        environment = submitter.instance_env(instance)

        # From current environment
        for var in [
            "MAYA_MODULE_PATH",
            "ARNOLD_PLUGIN_PATH",
        ]:
            environment[var] = os.getenv(var, "")

        return environment
