
import os
import json
import platform
import pyblish.api


class SubmitDeadlinePublish(pyblish.api.ContextPlugin):
    """Publish via running script on Deadline

    Submitting jobs per instance group to deadline.

    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Deadline Publish"

    targets = ["deadline"]

    def process(self, context):
        import reveries

        reveries_path = reveries.__file__
        script_file = os.path.join(os.path.dirname(reveries_path),
                                   "scripts",
                                   "deadline_publish.py")

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

        # Instance data

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            subset = instance.data["subset"]
            version = instance.data["versionNext"]

            deadline_pool = instance.data["deadlinePool"]
            deadline_group = instance.data["deadlineGroup"]
            deadline_prior = instance.data["deadlinePriority"]

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
                    "Group": deadline_group,
                    "Priority": deadline_prior,

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
                "EnvironmentKeyValue%d" % index: "{key}={value}".format(
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

            if "payloads" not in context.data:
                context.data["payloads"] = list()

            context.data["payloads"].append(payload)

    def assemble_environment(self, instance):
        """Compose submission required environment variables for instance

        Return:
            environment (dict): A set of remote variables, return `None` if
                instance is not assigning to remote site or publish is
                disabled.

        """
        context = instance.context
        index = context.index(instance)

        # From context
        environment = context.data["deadlineSubmitter"].context_env()

        # Save Instances' name and version
        #
        # instance subset name
        key = "AVALON_DELEGATED_SUBSET_%d" % index
        environment[key] = instance.data["subset"]
        #
        # instance subset version
        #
        # This should prevent version bump when re-running publish with
        # same params.
        #
        key = "AVALON_DELEGATED_VERSION_NUM_%d" % index
        environment[key] = instance.data["versionNext"]

        return environment
