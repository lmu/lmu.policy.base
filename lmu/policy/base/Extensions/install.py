def uninstall(portal):
    setup_tool = portal.portal_setup
    setup_tool.runAllImportStepsFromProfile(
        'profile-lmu.policy.base:uninstall')
