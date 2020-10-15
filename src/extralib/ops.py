
from .util import has_method, is_primitive, first, last, is_empty

def clone(value, deep=False):
    if is_primitive(value):
        return value
    elif isinstance(value, list):
        if not deep:
            return list(value)
        return list(clone(el, deep=True) for el in value)
    elif isinstance(value, dict):
        if not deep:
            return dict(value)
        return dict((clone(k, deep=True), clone(v, deep=True)) for (k, v) in value.items())
    elif has_method(value, 'clone'):
        return value.clone(deep=deep)
    else:
        raise NotImplementedError(f"did not know how to clone {value}")

def equal(a, b):
    if is_primitive(a) and is_primitive(b):
        return a == b
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        for el1, el2 in zip(a, b):
            if not equal(el1, el2):
                return False
        return True
    elif isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        for (k1, v1), (k2, v2) in zip(a.items(), b.items()):
            if not equal(k1, k2) or not equal(v1, v2):
                return False
        return True
    elif has_method(type(a), 'equal') and has_method(type(b), 'equal'):
        try:
            return a.equal(b)
        except TypeError:
            return b.equal(a)
    else:
        raise TypeError(f'values {a} and {b} are not comparable')

def resolve(value, key):
    if has_method(key, 'resolve'):
        return key.resolve(value)
    return value[key]

def increment_key(value, key):
    if has_method(key, 'increment'):
        return key.increment(value)
    elif isinstance(key, int):
        return key+1 if key < len(value)-1 else None
    elif isinstance(key, str):
        items = iter(value.items())
        for k, v in items:
            if k == key:
                break
        try:
            return next(items)[0]
        except StopIteration:
            return None
    raise RuntimeError(f'did not know how to increment key {key}')

def decrement_key(value, key):
    if has_method(key, 'decrement'):
        return key.decrement(value)
    elif isinstance(value, list):
        return key-1 if key > 0 else None
    elif isinstance(key, str):
        last_key = None
        for k, v in value.items():
            if k == key:
                break
            last_key = k
        return last_key
    else:
        raise RuntimeError(f'did not know how to decrement key {key}')

TYPE_INDICES = [bool, int, float, str, tuple, list]

def is_char(v):
    return isinstance(v, str) and len(v) == 1

# NOTE We explicitly distinguish between a str and a char because string
# comparison in python sometimes yields incorrect results.
def lt(v1, v2):
    if (isinstance(v1, bool) and isinstance(v2, bool)) \
            or (isinstance(v1, int) and isinstance(v2, int)) \
            or (isinstance(v1, float) and isinstance(v2, float)) \
            or (is_char(v1) and is_char(v2)):
        return v1 < v2
    elif (isinstance(v1, tuple) and isinstance(v2, tuple)) \
            or (isinstance(v1, list) and isinstance(v2, list)) \
            or (isinstance(v1, str) and isinstance(v2, str)):
        if (len(v1) != len(v2)):
            return len(v1) < len(v2)
        for el1, el2 in zip(v1, v2):
            if lt(el1, el2):
                return True
        return False
    else:
        return TYPE_INDICES.index(v1.__class__) < TYPE_INDICES.index(v2.__class__)

def lte(v1, v2):
    return lt(v1, v2) or equal(v1, v2)

def gte(v1, v2):
    return not lt(v1, v2)

def gt(v1, v2):
    return not le(v1, v2)

# def is_expandable(value):
#     return isinstance(value, list) \
#         or isinstance(value, tuple) \
#         or isinstance(value, dict) \
#         or has_method(value, 'expand')

def is_iterator(value):
    return has_method(value, '__next__')

def expand(value):
    if isinstance(value, list) or isinstance(value, tuple):
        for i in range(0, len(value)):
            yield i, value[i]
    elif isinstance(value, dict):
        yield from value.items()
    elif has_method(value, 'expand'):
        yield from value.expand()
    else:
        pass

class Path:

    def __init__(self, elements):
        self.elements = elements

    def __bool__(self):
        return len(self.elements) > 0

    def __len__(self):
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)

    def __str__(self):
        return f'Path({str(self.elements)})'

    def clone(self, deep=False):
        return Path(clone(self.elements, deep=deep))

    def resolve(self, root):
        result = root
        for key in self.elements:
            result = resolve(result, key)
        return result

    def is_first(self, root):
        return len(self.elements) == 0

    def is_end(self, root):

        # pre-populate a list of child nodes of self.root so we can access them
        # easily
        value = root
        values = [ value ]
        for key in self.elements:
            value = resolve(value, key)
            values.append(value)

        # if we still can go deeper we should try that first
        if is_expandable(value):
            return False

        # go up until we find a key that we can increment
        for i in reversed(range(0, len(self.elements))):
            key = self.elements[i]
            new_key = increment_key(values[i], key)
            if new_key is not None:
                return False

        # we were unable to find a new path, so this must be the end
        return True

    def increment(self, root, expand=expand):

        # pre-populate a list of child nodes of self.root so we can access them
        # easily
        value = root
        values = [ value ]
        for key in self.elements:
            value = resolve(value, key)
            values.append(value)

        # if we still can go deeper we should try that first
        result = first(expand(value))
        if result is not None:
            key, child = result
            new_elements = clone(self.elements)
            new_elements.append(key)
            # self.elements.append(key)
            return Path(new_elements)
            # return

        # go up until we find a key that we can increment
        for i in reversed(range(0, len(self.elements))):
            key = self.elements[i]
            new_key = increment_key(values[i], key)
            if new_key is not None:
                # del self.elements[i:]
                new_elements = self.elements[:i]
                new_elements.append(new_key)
                # self.elements.append(new_key)
                return Path(new_elements)
                # return

        # raise RuntimeError(f'cannot increment this cursor becaue it is at its end')

    def decrement(self, root, expand=expand):

        # pre-populate a list of child nodes of self.root so we can access them
        # easily
        last_value_parent = None
        value = root
        for key in self.elements:
            last_value_parent = value
            value = resolve(value, key)

        if not self.elements:
            return None
            # raise RuntimeError(f'cannot decrement this cursor because it is at the beginning')

        key = self.elements[-1]
        new_key = decrement_key(last_value_parent, key)

        if new_key is None:
            # del self.elements[-1]
            # return
            return Path(self.elements[:-1])

        # del self.elements[-1]
        # self.elements.append(new_key)
        new_elements = self.elements[:-1]
        new_elements.append(new_key)

        # get the rightmost node relative to the node on the new key
        value = resolve(last_value_parent, new_key)
        while True:
            result = last(expand(value))
            if result is None:
                break
            child_key, value = result
            # self.elements.append(child_key)
            new_elements.append(child_key)

        return Path(new_elements)
