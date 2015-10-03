from Products.CMFCore import permissions
from Products.CMFPlone.PloneBatch import Batch
from lmu.policy.base.browser import str2bool
from lmu.policy.base.browser.content import _AbstractLMUBaseContentView
from plone import api


class _AbstractLMUBaseListingView(_AbstractLMUBaseContentView):

    DEFAULT_LIMIT = 10
    portal_type = None
    container_interface = None
    sort_on = 'effective'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        limit_display = getattr(self.request, 'limit_display', None)
        limit_display = int(limit_display) if limit_display is not None else \
            self.DEFAULT_LIMIT
        b_size = getattr(self.request, 'b_size', None)
        self.b_size = int(b_size) if b_size is not None else limit_display
        b_start = getattr(self.request, 'b_start', None)
        self.b_start = int(b_start) if b_start is not None else 0

        self.content_filter = {'portal_type': self.portal_type}
        self.pcatalog = self.context.portal_catalog

    def absolute_length(self):
        return len(self.pcatalog.searchResults(self.content_filter))

    def entries(self):
        entries = []
        if self.container_interface.providedBy(self.context):

            entries = self.pcatalog.searchResults(
                self.content_filter,
                sort_on=self.sort_on, sort_order='reverse',
            )

        return entries

    def batch(self):
        batch = Batch(
            self.entries(),
            size=self.b_size,
            start=self.b_start,
            orphan=1
        )
        return batch

    def can_add(self):
        return api.user.has_permission(permissions.AddPortalContent,
                                       #'lmu.contenttypes.blog: Add Blog Entry',
                                       obj=self.context)


class _FrontPageIncludeMixin(object):

    def update(self):
        """
        """
        # Hide the editable-object border
        request = self.request
        request.set('disable_border', True)

    def __call__(self):
        omit = self.request.get('full')
        self.omit = not str2bool(omit)
        author = self.request.get('author')
        self.author = bool(author)
        if self.omit:
            REQUEST = self.context.REQUEST
            RESPONSE = REQUEST.RESPONSE
            RESPONSE.setHeader('Content-Type', 'text/xml;charset=utf-8')
        return self.template()
