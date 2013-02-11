# Copyright 2013 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# See COPYING for license information (LGPLv3)

from __future__ import print_function

import json
import functools


class NotCachedError(Exception):
    """
    Exception raised if uncached object is being accessed in CACHE_PURE mode
    """
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr

    def __str__(self):
        return "%s has no cached response for %s" % (self.obj, self.attr)


class CachedException(object):
    """
    Container wrapper for cached exceptions
    """

    __slots__ = ['exc']

    def __init__(self, exc):
        self.exc = exc


class GhostObject(object):
    """
    Replacement for real object used when working from cache
    """


def specialmethod(func):
    @functools.wraps(func)
    def helper(self, *args):
        key_func = lambda: (func.__name__,) + (args)
        impl_func = lambda obj: (getattr(obj, func.__name__)(*args))
        return CachingProxy._CachingProxy__cache_resolve(
            self, key_func, impl_func)
    return helper


def specialmethod_nocache(func):
    @functools.wraps(func)
    def helper(self, *args):
        return getattr(self._CachingProxy__obj, func.__name__)(*args)
    return helper


class CachingProxy(object):

    REPR_REAL, REPR_FAKE = range(2)

    repr_mode = REPR_REAL

    @classmethod
    def set_repr_mode(cls, mode):
        """
        Set __repr__() mode.

        There are two modes:

            REPR_REAL - show real repr() on all CachingProxy instances
            REPR_FAKE - show the repr() of wrapped object

        By default, REPR_REAL is used so each cached object will
        be easily identifieable as such.
        """
        cls.repr_mode = True

    def __repr__(self):
        if CachingProxy.repr_mode == CachingProxy.REPR_REAL:
            return ("<CachingProxy over %r with keys:%r values:%r"
                    " at %#0xlp>" % (
                        self.__obj, self.__keys, self.__values, id(self)))
        elif CachingProxy.repr_mode == CachingProxy.REPR_FAKE:
            key_func = lambda: '__repr__'
            impl_func = lambda obj: obj.__repr__()
            try:
                return self.__cache_resolve(key_func, impl_func)
            except NotCachedError:
                return ("<(fallback mode)CachingProxy over %r with keys:%r"
                        " values:%r at %#0xlp>") % (
                            self.__obj, self.__keys, self.__values, id(self))

    CACHE_NONE, CACHE_KEEP, CACHE_USE, CACHE_PURE = range(4)

    cache_mode = CACHE_NONE

    @classmethod
    def set_cache_mode(cls, mode):
        """
        Set cache mode / behavoir.

        There are four available modes:

            CACHE_NONE - Cache is entirely disabled.

                         All method calls are directly forwarded and the
                         results (and cache keys, if needed) are not stored or
                         computed.

            CACHE_KEEP - Cache is enabled but never used to produce responses.

                         This mode will allow the caller to observe different
                         return values from a two calls to a single method if
                         the backing implementation would return those.

            CACHE_USE -  Cache is used if cached response exists.

                         This mode allows to use the cache to remove operations
                         assuming that all computation is purely functional and
                         depends on their arguments (which may not be true)
                         Missing cache values call into the backing
                         implementation

            CACHE_PURE - Cache is the only data source.

                         This mode never calls into the backing implementation.
                         As long as all responses are known it behaves as
                         CACHE_USE for any missing cache keys it raises
                         NotCachedError()

        By default cache is using the CACHE_NONE behavior to behave as if
        nothing was being intercepted and not to consume extra memory.
        It should be safe for all kinds of code.
        """
        cls.cache_mode = mode

    def __cache_resolve(self, key_func, impl_func):
        keys = self.__keys
        values = self.__values
        obj = self.__obj

        def call_key():
            return key_func()

        def call_impl():
            try:
                value = impl_func(obj)
            except Exception as exc:
                import logging
                logging.exception("wrapping boom")
                return exc
            else:
                return CachingProxy(value)

        def store(cache_key, wrapped_value):
            try:
                index = keys.index(cache_key)
            except ValueError:
                keys.append(cache_key)
                values.append(wrapped_value)
            else:
                keys[index] = cache_key
                values[index] = wrapped_value

        def lookup(cache_key):
            try:
                index = keys.index(cache_key)
            except ValueError:
                raise
            else:
                return values[index]

        def return_wrapped(wrapped_value):
            if isinstance(wrapped_value, CachedException):
                raise CachingProxy(wrapped_value.exc)
            else:
                return wrapped_value

        if CachingProxy.cache_mode == CachingProxy.CACHE_NONE:
            # Directly call value (no wrapping!)
            return impl_func(obj)
        elif CachingProxy.cache_mode == CachingProxy.CACHE_KEEP:
            # Compute value and wrap
            wrapped_value = call_impl()
            # Compute cache key
            cache_key = call_key()
            # Keep wrapped value in cache
            store(cache_key, wrapped_value)
            # Unwrap and return / raise wrapped value
            return return_wrapped(wrapped_value)
        elif CachingProxy.cache_mode == CachingProxy.CACHE_USE:
            # Compute cache key
            cache_key = call_key()
            # Look for cached, wrapped value
            try:
                wrapped_value = lookup(cache_key)
            except ValueError:
                # Compute value and wrap
                wrapped_value = call_impl()
                # Keep wrapped value in cache
                store(cache_key, wrapped_value)
            # Unwrap and return / raise wrapped value
            return return_wrapped(wrapped_value)
        elif CachingProxy.cache_mode == CachingProxy.CACHE_PURE:
            # Compute cache key
            cache_key = call_key()
            # Look for cached, wrapped value
            try:
                wrapped_value = lookup(cache_key)
            except ValueError:
                # Raise special exception when cache is empty
                raise NotCachedError(obj, cache_key)
            else:
                # Unwrap and return / raise cached wrapped value
                return return_wrapped(wrapped_value)

    __slots__ = ['_CachingProxy__obj', '_CachingProxy__keys',
                 '_CachingProxy__values']

    def __new__(cls, obj):
        # Don't wrap over primitive non-container, immutable types
        if isinstance(obj, (bool, float, int, str, unicode)) or obj is None:
            return obj
        else:
            return super(CachingProxy, cls).__new__(cls, obj)

    def __init__(self, obj):
        object.__setattr__(self, "_CachingProxy__obj", obj)
        object.__setattr__(self, "_CachingProxy__keys", [])
        object.__setattr__(self, "_CachingProxy__values", [])

    @specialmethod
    def __str__(self):
        pass

    @specialmethod
    def __len__(self):
        pass

    @specialmethod
    def __lt__(self, other):
        pass

    @specialmethod
    def __le__(self, other):
        pass

    @specialmethod
    def __eq__(self, other):
        pass

    @specialmethod
    def __ne__(self, other):
        pass

    @specialmethod
    def __gt__(self, other):
        pass

    @specialmethod
    def __ge__(self, other):
        pass

    @specialmethod
    def __cmp__(self, other):
        pass

    @specialmethod
    def __hash__(self):
        pass

    @specialmethod
    def __nonzero__(self):
        pass

    @specialmethod
    def __unicode__(self):
        pass

    @specialmethod
    def __isinstance__(self, instance):
        pass

    @specialmethod
    def __subclasscheck__(self, subclass):
        pass

    def __call__(self, *args, **kwargs):
        key_func = lambda: ('__call__', args, kwargs)
        impl_func = lambda obj: obj(*args, **kwargs)
        return self.__cache_resolve(key_func, impl_func)

    @specialmethod
    def __getitem__(self, key):
        pass

    @specialmethod_nocache
    def __setitem__(self, key, value):
        pass

    @specialmethod_nocache
    def __delitem__(self, key):
        pass

    @specialmethod
    def __iter__(self):
        pass

    @specialmethod
    def __reversed__(self):
        pass

    @specialmethod
    def __contains__(self, item):
        pass

    def __getattribute__(self, attr):
        # Allow real access to the two special values
        if attr in ('_CachingProxy__obj', '_CachingProxy__keys',
                    '_CachingProxy__values', '_CachingProxy__cache_resolve'):
            return object.__getattribute__(self, attr)
        # Skip wrapping on some special things
        if attr in ("__class__", "__dict__"):
            return getattr(self, attr)
        # Return values that are in cache directly
        key_func = lambda: ('__getattribute__', attr)
        impl_func = lambda obj: getattr(obj, attr)
        return self.__cache_resolve(key_func, impl_func)

    @classmethod
    def _to_json_obj(cls, instance):
        return {
            'CachingProxy': True,
            'keys': instance.__keys,
            'values': instance.__values
        }

    @classmethod
    def _from_json_obj(cls, json_obj):
        self = cls(GhostObject)
        keys = self.__keys = []
        # Transform lists to tuples as that information is lost after
        # running json.loads(json.dumps(...)) and list.index() depends on it
        for key in json_obj['keys']:
            if isinstance(key, list):
                keys.append(tuple(key))
            else:
                keys.append(key)
        # Transform dicts with 'CachingProxy' in them to instances
        values = self.__values = []
        for value in json_obj['values']:
            if isinstance(value, dict) and "CachingProxy" in value:
                values.append(cls._from_json_obj(value))
            else:
                values.append(value)
        return self

    @classmethod
    def to_cache(cls, instance):
        return json.dumps(instance, default=cls._to_json_obj)

    @classmethod
    def from_cache(cls, cache):
        json_obj = json.loads(cache)
        return cls._from_json_obj(json_obj)


def demo():
    class FooMaker(object):

        @property
        def foo(self):
            return self.get_foo()

        def get_foo(self):
            print("Computing foo...")
            return "foo"

    # maker = CachingProxy(FooMaker())

    from launchpadlib.launchpad import Launchpad

    def use_lp(lp):
        print("Launchpad object is", repr(lp))
        repr(lp.bugs)
        repr(lp.bugs[1])
        print("Link to first bug is", lp.bugs[1].web_link)

    # Use fake repr() so that none of the proxy is visible
    CachingProxy.set_repr_mode(CachingProxy.REPR_FAKE)
    # Record everything in memory but don't use it
    CachingProxy.set_cache_mode(CachingProxy.CACHE_KEEP)
    # Create a real launchpad object
    lp = CachingProxy(Launchpad.login_anonymously("testapp"))
    # Use launchpad object somehow
    print("USING REAL OBJECT")
    use_lp(lp)
    # Save the cache
    cache = CachingProxy.to_cache(lp)
    # Create a dummy from the cache
    lp2 = CachingProxy.from_cache(cache)
    # Switch to pure mode -- we're working on fake objects anyway
    CachingProxy.set_cache_mode(CachingProxy.CACHE_PURE)
    # Use the fake launchpad object in the same way as before
    print("USING FAKE OBJECT")
    use_lp(lp2)
