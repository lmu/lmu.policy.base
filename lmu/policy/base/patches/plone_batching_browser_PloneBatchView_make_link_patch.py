from plone.batching.browser import PloneBatchView
from ZTUtils import make_query
import logging

logger = logging.getLogger('Batch Patch')


def make_link(self, pagenumber=None):
    form = self.request.form
    if self.batchformkeys:
        batchlinkparams = dict([(key, form[key])
                                for key in self.batchformkeys
                                if key in form])
    else:
        batchlinkparams = form.copy()

    start = max(pagenumber - 1, 0) * self.batch.pagesize
    return '%s?%s' % (self.context.absolute_url(),
                      make_query(batchlinkparams, {self.batch.b_start_str: start}))

PloneBatchView.make_link = make_link
logger.info("Patching plone.batching.browser.PloneBatchView.make_link")
