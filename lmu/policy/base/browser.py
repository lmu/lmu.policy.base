from Products.CMFCore.utils import getToolByName
from plone.app.search.browser import Search as BaseSearch


class Search(BaseSearch):

    def extra_types(self):
        ptool = getToolByName(self, 'portal_properties')
        siteProperties = getattr(ptool, 'site_properties')
        extraTypes = siteProperties.getProperty('extra_types_searched', [])
        return list(extraTypes)

    def filter_query(self, query):
        query = super(Search, self).filter_query(query)
        if query:
            if 'path' in query:
                del query['path']
            query['portal_type'] += self.extra_types()
        return query

    def types_list(self):
        types = super(Search, self).types_list()
        return types + self.extra_types()
