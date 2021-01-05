
import pyblish.api


class ValidateLookDevHasDependency(pyblish.api.InstancePlugin):
    """Validate LookDev Has Dependency

    在 USD 中 LookDev 與 model 之間必須要有 dependency

    你的 Subset Set 需要看起來像這樣(以 Asset Robot 舉例):

    - lookDefault
        L Robot_model_01_:ROOT

    也就是你的 model 必須是reference, 如果不是, 也請重新 reference 一個新的進來
    詳情請參考 KnowHow 上關於 LookDev publish 的相關內容

    """

    order = pyblish.api.ValidatorOrder + 0.491

    label = "Validate LookDev Dependency"
    hosts = ["maya"]
    families = [
        "reveries.look"
    ]

    def process(self, instance):
        if not instance.data.get("model_subset_id"):
            raise RuntimeError("{}: Get model dependency failed".format(instance))

        # subset_id = ""
        # root_container_data = instance.context.data.get(
        #     "RootContainers")
        # for container_name, container_data in root_container_data.items():
        #     if container_data["loader"] == "ModelLoader":
        #         subset_id = container_data.get("subsetId", "")
        # instance.data["model_subset_id"] = subset_id
