import hashlib
import pickle
import types

def _update_int(myint, hash):
    hash.update(str(myint).encode())

def _update_str(mystr, hash):
    hash.update(mystr.encode())

def _update_bytes(mybytestr, hash):
    hash.update(mybytestr)

def _update_iterable(items, hash):
    for item in items:
        update(item, hash)

def _update_dict(mydict, hash):
    items = sorted(mydict.items())
    _update_iterable(items, hash)

def _update_set(myset, hash):
    _update_iterable(sorted(myset), hash)

def _update_module(mymodule, hash):
    hash.update(mymodule.__name__.encode())

def _update_function(myfunction, hash):
    hash.update(myfunction.__module__.encode())
    hash.update(myfunction.__name__.encode())


update_by_type = { \
    int : _update_int,
    str : _update_str,
    bytes : _update_bytes,
    list : _update_iterable,
    tuple : _update_iterable,
    dict : _update_dict,
    set : _update_set,
    types.ModuleType : _update_module,
    types.FunctionType : _update_function,
}


def update(obj, hash):
    """General hash updater that works for everything."""
    typ = type(obj)
    hash.update(typ.__module__.encode())
    hash.update(typ.__name__.encode())

    try:
        updater = update_by_type[typ]
        updater(obj,hash)
    except KeyError:
        try:
            obj.update_hash(hash)
        except AttributeError:
            # Try different collection update methods
            if isinstance(obj, dict):
                _update_dict(obj, hash)
            elif isinstance(obj, set):
                _update_set(obj, hash)

def hexdigest(obj, hash_type='md5'):
    hash = getattr(hashlib, hash_type)()
    update(obj, hash)
    return hash.hexdigest()
