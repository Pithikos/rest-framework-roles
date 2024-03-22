import os
import sys
import re
import subprocess
import shlex

try:
    from setuptools import setup
    from setuptools.command.install import install
except ImportError:
    from distutils.core import setup
    from distutils.command.install import install


VERSION = '1.0.6'


def get_tag_version():
    cmd = 'git tag --points-at HEAD'
    versions = subprocess.check_output(shlex.split(cmd)).splitlines()
    if not versions:
        return None
    if len(versions) != 1:
        sys.exit(f"Trying to get tag via git: Expected excactly one tag, got {len(versions)}")
    version = versions[0].decode()
    if re.match('^v[0-9]', version):
        version = version[1:]
    return version


class VerifyVersionCommand(install):
    """ Custom command to verify that the git tag matches our version """
    description = 'verify that the git tag matches our version'

    def run(self):
        tag_version = get_tag_version()
        if tag_version and tag_version != VERSION:
            sys.exit(f"Git tag: {tag} does not match the version of this app: {VERSION}")


INSTALL_REQUIRES = [
    "djangorestframework",
]


setup(
    name='rest_framework_roles',
    version=VERSION,
    description='Role-based permissions for Django REST Framework and vanilla Django.',
    author='Johan Hanssen Seferidis',
    author_email='manossef@gmail.com',
    packages=['rest_framework_roles'],
    url='https://github.com/Pithikos/rest-framework-roles',
    license='LICENSE',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=INSTALL_REQUIRES,
    python_requires='>=3',
    keywords=[
        'permissions',
        'roles',
        'users',
        'django',
        'rest',
        'drf',
        'acl',
        'security',
        'rest framework',
        'access control'
    ],
    classifiers=[
        'Framework :: Django',
        'Topic :: Security',
    ],
    cmdclass={
        'verify': VerifyVersionCommand,
    },
)
