import os
import subprocess
import Deadline.Events


def GetDeadlineEventListener():
    return AvalonIntegrateOnJobFinish()


def CleanupDeadlineEventListener(eventListener):
    eventListener.Cleanup()


class AvalonIntegrateOnJobFinish(Deadline.Events.DeadlineEventListener):

    def __init__(self):
        self.OnJobFinishedCallback += self.OnJobFinished

    def Cleanup(self):
        del self.OnJobFinishedCallback

    def OnJobFinished(self, job):
        # (NOTE) Will be executed by the slave which complete the last task of
        #        the job.
        #
        #        Any change in this script or plugin configuration will need
        #        time to pass to the running slave. May need to re-launch the
        #        slave.
        #
        #        Event plugin's error only shows in slave log.
        #

        required_env = [
            "PYTHONPATH",
            "AVALON_MONGO",
            "PYBLISH_DUMP_FILE",
        ]

        job_environ = job.GetJobEnvironmentKeys()
        if not all(key in job_environ for key in required_env):
            # Not a valid Avalon job
            return

        if "AVALON_POST_TASK_SCRIPTS" in job_environ:
            post = job.GetJobExtraInfoKeyValue("AVALON_POST_TASK_SCRIPTS")
            if "publish_by_task" in post:
                # Progressive publish job
                return

        print("Avalon job found, prepare to run publish..")

        python = job.GetJobExtraInfoKeyValueWithDefault(
            "PYBLISH_FILESYS_EXECUTABLE",
            self.GetConfigEntry("PythonExecutable")
        )
        script = job.GetJobExtraInfoKeyValueWithDefault(
            "PYBLISH_FILESYS_SCRIPT",
            self.GetConfigEntry("PublishScript")
        )
        dumpfile = job.GetJobEnvironmentKeyValue("PYBLISH_DUMP_FILE")

        # Check resources
        if not os.path.isfile(python):
            raise Exception("Python executable not found: %s" % python)
        if not os.path.isfile(script):
            raise Exception("Publish script not found: %s" % script)
        if not os.path.isfile(dumpfile):
            raise Exception("Publish dump file not found: %s" % dumpfile)

        # Assume all tasks completed, run filesys integration
        args = [
            python,
            script,
            "--dump",
            dumpfile,
        ]
        environ = {
            key: os.environ[key]
            for key in ("USERNAME",
                        "SYSTEMROOT",
                        "PYTHONPATH",
                        "PATH")
            if key in os.environ
        }
        environ.update({
            # could be unicode..
            str(key): str(job.GetJobEnvironmentKeyValue(key))
            for key in job_environ
        })
        popen = subprocess.Popen(args,
                                 env=environ,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        output, _ = popen.communicate()
        print(output)
        if popen.returncode != 0:
            raise Exception("Publish failed, see log..")
