import logging
from plone import api

log = logging.getLogger(__name__)


def setupVarious(context):
    """Install all additional Things that can't be done via Generic Setup
    """

    if context.readDataFile('lmu.policy.base_default.txt') is None:
        return

    _setupAutoRoleHeader(context)


def _setupAutoRoleHeader(context):
    acl_users = api.portal.get_tool('acl_users')
    if 'auto_role_header' not in acl_users.objectIds():
        log.warn('auto_role_header not found, please install'
                 ' AutoRoleFromHostHeader!')
    auto_role = acl_users['auto_role_header']
    auto_role.manage_changeProperties(
        match_roles=('Groupmembership; cms-admins-insp; Site Administrator',)
    )
