import copy


class DelayRunBuilder(object):
    def __init__(self, instance):
        self.delete_data = []
        self.instance_data = {}
        self.context_data = {}

        self._copy_dict(instance)

    def __remove_item(self, _data):
        _data.pop("_cache_nodes", None)
        return _data

    def _copy_dict(self, instance):
        self.delete_data = []

        _data = self.__remove_item(dict(instance.data))
        instance_data = copy.deepcopy(_data)

        self.walk_dict(instance_data)
        self.instance_data = self.delete_keys_from_dict(
            instance_data, self.delete_data
        )

        self.delete_data = []
        context_data = dict(instance.context.data).copy()
        self.walk_dict(context_data)
        self.context_data = self.delete_keys_from_dict(
            context_data, self.delete_data)

    def walk_dict(self, d):
        for k, v in sorted(d.items(), key=lambda x: x[0]):
            if isinstance(v, dict):
                self.walk_dict(v)
            elif hasattr(v, '__dict__'):
                self.delete_data.append(k)
            elif isinstance(v, list):
                for _v in v:
                    if hasattr(_v, '__dict__'):
                        self.delete_data.append(k)
                        continue

    def delete_keys_from_dict(self, dictionary, keys):
        from collections import MutableMapping

        keys_set = set(keys)

        modified_dict = {}
        for key, value in dictionary.items():
            if key not in keys_set:
                if isinstance(value, MutableMapping):
                    modified_dict[key] = \
                        self.delete_keys_from_dict(value, keys_set)
                else:
                    modified_dict[key] = value
        return modified_dict
