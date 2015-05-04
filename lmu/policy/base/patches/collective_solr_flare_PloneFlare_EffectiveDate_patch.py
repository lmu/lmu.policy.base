import logging

from collective.solr.flare import PloneFlare
from DateTime import DateTime

logger = logging.getLogger('Search Patch')

timezone = DateTime().timezone()


@property
def EffectiveDate(self):
    effective = self.get('effective', None)
    if effective is None:
        return 'n.a.'
    return effective.toZone(timezone).ISO8601()


PloneFlare.EffectiveDate = EffectiveDate
logger.info("Patching collective.solr.flare.PloneFlare.EffectiveDate")
