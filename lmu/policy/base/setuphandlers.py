import logging
from plone import api

log = logging.getLogger(__name__)


def setupVarious(context):
    """Install all additional Things that can't be done via Generic Setup
    """

    if context.readDataFile('lmu.policy.base_default.txt') is None:
        return

    _setupAutoRoleHeader(context)
    _setupAutoUserMaker(context)


def _setupAutoRoleHeader(context):
    acl_users = api.portal.get_tool('acl_users')
    if 'auto_role_header' not in acl_users.objectIds():
        log.warn('auto_role_header not found, please install'
                 ' AutoRoleFromHostHeader!')
    auto_role = acl_users['auto_role_header']
    auto_role.manage_changeProperties(
        match_roles=('Groupmembership; cms-admins-insp; Site Administrator',)
    )


def _setupAutoUserMaker(context):
    acl_users = api.portal.get_tool('acl_users')
    if 'AutoUserMakerPASPlugin' not in acl_users.objectIds():
        log.warn('AutoUserMakerPASPlugin not found, please install'
                 ' AutoUserMakerPASPlugin!')
    auto_user = acl_users['AutoUserMakerPASPlugin']
    auto_user.manage_changeProperties(
        http_remote_user='HTTP_EDUPersonPrincipalName',
        http_commonname='HTTP_DISPLAYNAME',
        http_email='HTTP_MAIL',
        auto_update_user_properties=1,
    )
