from setuptools import setup, find_packages
import os

version = '1.0'

setup(name='lmu.policy.base',
      version=version,
      description="A policy for lmu portals",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "Programming Language :: Python",
      ],
      keywords='',
      author='',
      author_email='',
      url='http://svn.plone.org/svn/collective/',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['lmu', 'lmu.policy'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'z3c.jbot',
          'collective.solr',
          'collective.indexing',
          'collective.quickupload',
          'plone.app.changeownership',
          # -*- Extra requirements for Plone 4 -*-
          'wildcard.foldercontents',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
