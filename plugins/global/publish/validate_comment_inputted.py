import pyblish.api


class ValidateCommentInputted(pyblish.api.ContextPlugin):
    """One must say something before publish
    """

    label = "Validate Publish Comment"
    order = pyblish.api.ValidatorOrder - 0.49995

    def process(self, context):
        project = context.data["projectDoc"]
        allow_no_comment = project["data"].get("allowNoComment")
        if allow_no_comment:
            self.log.info("Allow no comment, skipping..")
            return

        comment = context.data["comment"].strip()
        assert comment, "Please write a comment."
        self.log.info("Comment provided.")
