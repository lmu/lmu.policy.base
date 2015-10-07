from z3c.form.interfaces import IFormLayer
from zope.interface import Interface


class IProductLayer(Interface):
    """Marker for our product"""


class ILMUBaseThemeLayer(Interface):
    """Marker interface that defines a Zope 3 browser layer.
    """


class ILMUCommentFormLayer(IFormLayer):
    """ A form layer that helps us overrride ploneform-render-widget
    """


class ILMUContent(Interface):
    """Base interface for LMU specific content types"""
