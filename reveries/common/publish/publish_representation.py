from avalon import io, api


def publish(version_id, name, **kwargs):
    _data = kwargs.get('data', {})

    representations_context = {
        'data': _data,
        'type': 'representation',
        'name': name,
        'parent': version_id,
        'schema': 'avalon-core:representation-2.0'
    }

    reps_id = io.insert_one(representations_context).inserted_id

    return reps_id
