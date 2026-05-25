import copy
from functools import wraps
from collections import OrderedDict


class DeepCopyLRUCache:
    def __init__(self, capacity=500):
        self.cache = OrderedDict()
        self.capacity = capacity

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            if key in self.cache:
                self.cache.move_to_end(key)
                return copy.deepcopy(self.cache[key])
            result = func(*args, **kwargs)
            self.cache[key] = copy.deepcopy(result)
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
            return result
        return wrapper
