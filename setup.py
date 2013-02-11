#!/usr/bin/env python
# Copyright 2013 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# See COPYING for license information (LGPLv3)


from setuptools import setup


setup(
    name='cachingproxy',
    version='0.1',
    author="Zygmunt Krynicki",
    author_email="zkrynicki@gmail.com",
    py_modules=["cachingproxy"],
    description=(
        "CachingProxy magically records usage of arbitrary objects"
        " and allows you to replay the same behavior later (with serializable"
        " representation that can be stored on disk)"),
    url="https://github.com/zyga/cachingproxy")
