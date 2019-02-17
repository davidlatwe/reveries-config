
import pyblish.api
import avalon.api


class PublishReports(pyblish.api.ContextPlugin):
    """Report publish process results
    """

    label = "Reports (Please READ)"
    order = pyblish.api.IntegratorOrder + 0.49999

    def process(self, context):
        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        project = avalon.api.Session["AVALON_PROJECT"]
        silo = avalon.api.Session["AVALON_SILO"]
        asset = avalon.api.Session["AVALON_ASSET"]

        self.log.info("Publish Report")
        self.log.info("===")
        self.log.info("Project: {}".format(project))
        self.log.info("Silo: {}".format(silo))
        self.log.info("Asset: {}".format(asset))
        self.log.info("")

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            subset = instance.data["subset"]
            version = instance.data["versionNext"]

            self.log.info("Subset: {}".format(subset))
            self.log.info("Version: {}".format(version))

            self.log.info("Representations:")
            for package in instance.data["packages"]:
                publish_contractor = instance.data.get("publishContractor")

                self.log.info("    {}".format(package))
                self.log.info("    - Publish contractor: {}"
                              "".format(publish_contractor))

            self.log.info("")
