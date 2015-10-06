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
          # 'Products.ShibbolethPermissions',
          'lmu.contenttypes.blog',
          'lmu.contenttypes.pinnwand',
          'lmu.contenttypes.polls',
          'collective.deletepermission',
          'collective.indexing',
          'collective.quickupload',
          'collective.solr',
#          'pas.plugins.shibboleth_headers',
          'Pillow',
          'Plone',
          'plone.api',
          'plone.app.changeownership',
          'plone.app.contenttypes',
          'plone.app.layout',
          'plone.app.registry',
          'plone.directives.form',
          'plone.z3cform',
          'Products.AutoRoleFromHostHeader',
#          'Products.LongRequestLogger',
          'wildcard.foldercontents',
          'z3c.form',
          'z3c.jbot',
          'zope.app.schema',
          'zope.interface',
          'zope.schema',
          # -*- Extra requirements for Plone 4 -*-
      ],
      extras_require={
          'test': [
              'mock',
              'plone.app.testing',
              'plone.app.robotframework[debug]',
              'fake-factory',
          ],
          'develop': [
              'coverage',
              'flake8',
              'i18ndude',
              'Sphinx',
              'zptlint',
          ],
          'release': []
      },
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
