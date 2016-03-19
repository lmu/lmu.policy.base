from plone.dexterity.content import Container
from plone.app.discussion.interfaces import IConversation


class LMUBaseContent(Container):

    def get_discussion_count(self):
        try:
            # plone.app.discussion.conversation object
            # fetched via IConversation adapter
            conversation = IConversation(self)
        except Exception:
            return 0
        else:
            return conversation.total_comments

    def images(self):
        images = [item for item in self.values()if item.portal_type == 'Image']
        if None in images:
            images.remove(None)
        return images

    def files(self):
        files = [item for item in self.values() if item.portal_type == 'File']
        if None in files:
            files.remove(None)
        return files
