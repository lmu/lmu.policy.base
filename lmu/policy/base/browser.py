from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PythonScripts.standard import html_quote
from Products.PythonScripts.standard import url_quote_plus
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


class LivesearchReply(Search):

    template = ViewPageTemplateFile('templates/livesearch_reply2.pt')

    MAX_TITLE = 50
    MAX_DESCRIPTION = 150

    def searchterm_query(self):
        q = self.request.get('q', '')
        multispace = u'\u3000'.encode('utf-8')
        for char in ('?', '-', '+', '*', multispace):
            q = q.replace(char, ' ')
        searchterm_query = '?searchterm=%s' % url_quote_plus(q)
        return searchterm_query

    def searchterms(self, quote=True):
        q = self.request.get('q', '')

        def quotestring(s):
            return '"%s"' % s

        def quote_bad_chars(s):
            bad_chars = ["(", ")"]
            for char in bad_chars:
                s = s.replace(char, quotestring(char))
            return s

        # for now we just do a full search to prove a point, this is not the
        # way to do this in the future, we'd use a in-memory probability based
        # result set.
        # convert queries to zctextindex

        # XXX really if it contains + * ? or -
        # it will not be right since the catalog ignores all non-word
        # characters equally like
        # so we don't even attept to make that right.
        # But we strip these and these so that the catalog does
        # not interpret them as metachars
        # See http://dev.plone.org/plone/ticket/9422 for an explanation of
        # '\u3000'
        multispace = u'\u3000'.encode('utf-8')
        for char in ('?', '-', '+', '*', multispace):
            q = q.replace(char, ' ')
        r = q.split()
        r = " AND ".join(r)
        r = quote_bad_chars(r) + '*'
        if quote:
            return url_quote_plus(r)
        else:
            return r

    def display_title(self, full_title):
        return self.ellipse(full_title, self.MAX_TITLE)

    def display_description(self, full_description):
        return self.ellipse(full_description, self.MAX_DESCRIPTION)

    def ellipse(self, full_string, max_len):
        if (full_string and
                len(full_string) > max_len):
            display_string = ''.join(
                (full_string[:max_len], '...'))
        else:
            display_string = full_string
        return display_string

    def __call__(self):
        limit = self.request.get('limit', 10)
        path = self.request.get('path', None)

        REQUEST = self.context.REQUEST
        params = {'SearchableText': self.searchterms(quote=False),
                  'sort_limit': limit + 1}

        if path is not None:
            params['path'] = path

        pre_results = self.results(query=params, b_size=limit)

        RESPONSE = REQUEST.RESPONSE
        RESPONSE.setHeader('Content-Type', 'text/xml;charset=utf-8')

        results = []

        for result in pre_results:
            self.context.plone_log(result)
            # Only show Fiona Content in results that are from 'sp'
            if not result.getPath():
                continue
            elif not result.getPath().startswith('/prototyp-1'):
                results.append(result)
            elif result.getPath().startswith('/prototyp-1/sp'):
                results.append(result)

        self.live_results = results
        return self.template()
