from plone import api
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
        portal = api.portal.get()
        mtr = portal.mimetypes_registry
        files = [
            item
            for item
            in self.values()
            if item.portal_type == 'File' and mtr.lookup(item.file.contentType)[0].id != 'MPEG-4 video'
        ]
        if None in files:
            files.remove(None)
        return files

    def videos(self):
        portal = api.portal.get()
        mtr = portal.mimetypes_registry
        videos = [
            item
            for item
            in self.values()
            if item.portal_type == 'File' and mtr.lookup(item.file.contentType)[0].id == 'MPEG-4 video'
        ]
        if None in videos:
            videos.remove(None)
        return videos
