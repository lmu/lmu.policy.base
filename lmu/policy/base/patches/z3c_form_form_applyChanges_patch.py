import logging

import zope.component

from z3c.form import form
from z3c.form import interfaces
from z3c.form import util

logger = logging.getLogger('Batch Patch')


def applyChanges(form, content, data):
    changes = {}
    for name, field in form.fields.items():
        # If the field is not in the data, then go on to the next one
        try:
            newValue = data[name]
        except KeyError:
            continue
        # If the value is NOT_CHANGED, ignore it, since the widget/converter
        # sent a strong message not to do so.
        if newValue is interfaces.NOT_CHANGED:
            continue
        if util.changedField(field.field, newValue, context=content) or field.field.defaultFactory:
            # Only update the data, if it is different
            dm = zope.component.getMultiAdapter(
                (content, field.field), interfaces.IDataManager)
            dm.set(newValue)
            # Record the change using information required later
            changes.setdefault(dm.field.interface, []).append(name)
    return changes

form.applyChanges = applyChanges
logger.info("Patching z3c.form.form.applyChanges")
