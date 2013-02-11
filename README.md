CachingProxy
============

Proxy for interacting with something (which is slow and otherwise unwieldy to
change) recording all the interactions and then replaying that without
interacting with the original object.

Let's say you have some code that talks to launchpad and generates a report.
Each launchpad call / attribute reference is slow as it has to go across the
wire. The report you are writing needs some changes and has no infrastructure
for working against canned data.

Let's say you have some code that uses launchpad in the use\_lp() function:

    from launchpadlib.launchpad import Launchpad

    def use_lp(lp):
        print("Launchpad object is", repr(lp))
        repr(lp.bugs)
        repr(lp.bugs[1])
        print("Link to first bug is", lp.bugs[1].web_link)


Normally each time you call that it will take forever (longer than 30ms) to run
so iterating on it is unwieldy and annoying. Instead of doing it that way you
can record the interaction once, save it to a file and then keep editing
use\_lp() to do what you want. As long as you are still using all the proxied
objects the same way you can iterate quickly.

    # Use fake repr() so that none of the proxy is visible
    CachingProxy.set_repr_mode(CachingProxy.REPR_FAKE)
    # Record everything in memory but don't use it
    CachingProxy.set_cache_mode(CachingProxy.CACHE_KEEP)
    # Create a real launchpad object
    lp = CachingProxy(Launchpad.login_anonymously("testapp"))
    # Use launchpad object somehow
    print("USING REAL OBJECT")
    use_lp(lp)

The cache can be saved on disk and restored later, it does not depend on the
classes in your code in any way:

    # Save the cache
    cache = CachingProxy.to_cache(lp)

Now you can use a fake object created from the cache and call your functions
again:

    # Create a dummy from the cache
    lp2 = CachingProxy.from_cache(cache)

    # Switch to pure mode -- we're working on fake objects anyway
    CachingProxy.set_cache_mode(CachingProxy.CACHE_PURE)
    # Use the fake launchpad object in the same way as before
    print("USING FAKE OBJECT")
    use_lp(lp2)
