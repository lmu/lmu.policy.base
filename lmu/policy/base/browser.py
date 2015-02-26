from plone.app.search.browser import Search as BaseSearch


class Search(BaseSearch):

    def filter_query(self, query):
        query = super(Search, self).filter_query(query)
        if query:
            if 'path' in query:
                del query['path']
            query['portal_type'] += ["zuv_person"]
        return query

    def types_list(self):
        types = super(Search, self).types_list()
        return types + ["zuv_person"]
