from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
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

    def __call__(self):
        q = self.request.get('q', '')
        limit = self.request.get('limit', 10)
        path = self.request.get('path', None)

        ploneUtils = getToolByName(self.context, 'plone_utils')
        portal_url = getToolByName(self.context, 'portal_url')()
        plone_view = self.context.restrictedTraverse('@@plone')

        portalProperties = getToolByName(self.context, 'portal_properties')
        siteProperties = getattr(portalProperties, 'site_properties', None)
        useViewAction = []
        if siteProperties is not None:
            useViewAction = siteProperties.getProperty(
                'typesUseViewActionInListings', [])

        # SIMPLE CONFIGURATION
        MAX_TITLE = 50
        MAX_DESCRIPTION = 150

        # generate a result set for the query

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
        searchterms = url_quote_plus(r)

        REQUEST = self.context.REQUEST
        params = {'SearchableText': r,
                  'sort_limit': limit + 1}

        if path is not None:
            params['path'] = path

        pre_results = self.results(query=params, b_size=limit)

        searchterm_query = '?searchterm=%s' % url_quote_plus(q)

        RESPONSE = REQUEST.RESPONSE
        RESPONSE.setHeader('Content-Type', 'text/xml;charset=utf-8')

        # replace named entities with their numbered counterparts, in the xml
        # the named ones are not correct
        #   &darr;      --> &#8595;
        #   &hellip;    --> &#8230;
        label_no_results_found = _('label_no_results_found',
                                   default='No matching results found.')
        label_advanced_search = _('label_advanced_search',
                                  default='Advanced Search&#8230;')
        label_show_all = _('label_show_all', default='Show all items')

        ts = getToolByName(self.context, 'translation_service')

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

        output = []

        def write(s):
            output.append(safe_unicode(s))

        if not results:
            write('''<div class="LSIEFix">''')
            write('''<div id="LSNothingFound">%s</div>'''
                  % ts.translate(label_no_results_found, context=REQUEST))

            write('''<ul class="LSTable">''')

            write('''<li class="LSRow">''')
            write('<a href="%s" class="advancedsearchlink">%s</a>' %
                  (portal_url + '/search',
                  ts.translate(label_advanced_search, context=REQUEST)))
            write('''</li>''')
            write('''</ul>''')
            write('''</div>''')
        else:
            write('''<div class="LSIEFix">''')
            write('''<ul class="LSTable">''')
            for result in results[:limit]:
                #self.context.plone_log(str(result))
                icon = plone_view.getIcon(result)
                itemUrl = result.getURL()
                if result.portal_type in useViewAction:
                    itemUrl += '/view'

                itemUrl = itemUrl + searchterm_query

                itemUrl = itemUrl.replace('/functions/prototyp-1/sp', '')

                write('''<li class="LSRow">''')
                write(icon.html_tag() or '')
                #full_title = safe_unicode(pretty_title_or_id(result))
                full_title = safe_unicode(result.Title()) #get('Title','No Title set'))
                if full_title and len(full_title) > MAX_TITLE:
                    display_title = ''.join((full_title[:MAX_TITLE], '...'))
                else:
                    display_title = full_title

                full_title = full_title.replace('"', '&quot;')
                klass = 'contenttype-%s' \
                        % ploneUtils.normalizeString(result.portal_type)
                write('''<a href="%s" title="%s" class="%s">%s</a>'''
                      % (itemUrl, full_title, klass, display_title))
                display_description = safe_unicode(result.Description())
                if (display_description and
                        len(display_description) > MAX_DESCRIPTION):
                    display_description = ''.join(
                        (display_description[:MAX_DESCRIPTION], '...'))

                # need to quote it, to avoid injection of html containing
                # javascript and other evil stuff
                display_description = html_quote(display_description)
                write('''<div class="LSDescr">%s</div>''' %
                      (display_description))
                write('''</li>''')
                full_title, display_title, display_description = (
                    None, None, None)

            write('''<li class="LSRow">''')
            write('<a href="%s" class="advancedsearchlink advanced-search">'
                  '%s</a>' %
                  (portal_url + '/search',
                  ts.translate(label_advanced_search, context=REQUEST)))
            write('''</li>''')

            if len(results) > limit:
                # add a more... row
                write('''<li class="LSRow">''')
                searchquery = 'search?SearchableText=%s&path=%s' \
                    % (searchterms, params['path'])
                write('<a href="%s" class="advancedsearchlink show-all-items">'
                      '%s</a>' % (
                      searchquery,
                      ts.translate(label_show_all, context=REQUEST)))
                write('''</li>''')

            write('''</ul>''')
            write('''</div>''')

        return '\n'.join(output).encode('utf-8')
