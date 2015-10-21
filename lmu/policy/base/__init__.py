from AccessControl import allow_module
from zope.i18nmessageid import MessageFactory
import patches

patches  # flake8

allow_module('lmu.policy.base')
MESSAGE_FACTORY = MessageFactory('lmu.policy.base')
