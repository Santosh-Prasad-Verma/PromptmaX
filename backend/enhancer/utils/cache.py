import copy
import json
import threading
from functools import wraps
from collections import OrderedDict


def _make_hashable(value):
    try:
        hash(value)
        return value
    except TypeError:
        return json.dumps(value, sort_keys=True, default=str)


class DeepCopyLRUCache:
    def __init__(self, capacity=500):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = threading.RLock()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (
                tuple(_make_hashable(arg) for arg in args),
                tuple(sorted((name, _make_hashable(value)) for name, value in kwargs.items())),
            )
            with self.lock:
                if key in self.cache:
                    self.cache.move_to_end(key)
                    return copy.deepcopy(self.cache[key])
            result = func(*args, **kwargs)
            with self.lock:
                self.cache[key] = copy.deepcopy(result)
                if len(self.cache) > self.capacity:
                    self.cache.popitem(last=False)
            return result
        return wrapper
