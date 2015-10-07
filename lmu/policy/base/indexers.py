from Products.CMFCore.interfaces import IContentish
from lmu.policy.base.controlpanel import ILMUSettings
from plone.app.layout.navigation.root import getNavigationRoot
from plone.indexer import indexer
from plone.registry.interfaces import IRegistry
from zope.component import getUtility


@indexer(IContentish)
def domain(obj):
    registry = getUtility(IRegistry)
    lmu_settings = registry.forInterface(ILMUSettings)
    return lmu_settings.domain


@indexer(IContentish)
def cms_system(obj):
    registry = getUtility(IRegistry)
    lmu_settings = registry.forInterface(ILMUSettings)
    return lmu_settings.cms_system


@indexer(IContentish)
def context_path_string(obj):
    root_path = getNavigationRoot(obj)
    context_path = '/'.join(obj.getPhysicalPath())[len(root_path):]
    return context_path
