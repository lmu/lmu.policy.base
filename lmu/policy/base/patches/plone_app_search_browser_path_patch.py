from plone.app.search.browser import Search, EVER, quote_chars
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.browser.navtree import getNavigationRoot
import logging

logger = logging.getLogger('Search Patch')

def filter_query(self, query):
    request = self.request

    catalog = getToolByName(self.context, 'portal_catalog')
    valid_indexes = tuple(catalog.indexes())
    valid_keys = self.valid_keys + valid_indexes

    text = query.get('SearchableText', None)
    if text is None:
        text = request.form.get('SearchableText', '')
    if not text:
        # Without text, must provide a meaningful non-empty search
        valid = set(valid_indexes).intersection(request.form.keys()) or \
            set(valid_indexes).intersection(query.keys())
        if not valid:
            return

    for k, v in request.form.items():
        if v and ((k in valid_keys) or k.startswith('facet.')):
            query[k] = v
    if text:
        query['SearchableText'] = quote_chars(text)

    # don't filter on created at all if we want all results
    created = query.get('created')
    if created:
        try:
            if created.get('query') and created['query'][0] <= EVER:
                del query['created']
        except AttributeError:
            # created not a mapping
            del query['created']

    # respect `types_not_searched` setting
    types = query.get('portal_type', [])
    if 'query' in types:
        types = types['query']
    query['portal_type'] = self.filter_types(types)
    # respect effective/expiration date
    query['show_inactive'] = False
    # respect navigation root
    if 'path' not in query:
        query['path'] = getNavigationRoot(self.context)

    return query

Search.filter_query = filter_query
logger.info("Patching plone.app.search.Search.filter_query")
