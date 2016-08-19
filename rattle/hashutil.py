def hash_key(value):
    try:
        hash_key_fn = value._hash_key
    except AttributeError:
        pass
    else:
        return hash_key_fn()
    if isinstance(value, (tuple, list)):
        return (type(value),) + tuple(map(hash_key, value))
    elif isinstance(value, dict):
        return (type(value), frozenset(hash_key(tuple(value.items()))))
    else:
        return (type(value), value)


class HashInstance:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, HashInstance) and self.value is other.value

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return id(self.value)


class HashKey:
    def __init__(self, value):
        self.value = value
        self.key = hash_key(value)

    def __eq__(self, other):
        return isinstance(other, HashKey) and self.key == other.key

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.key)
