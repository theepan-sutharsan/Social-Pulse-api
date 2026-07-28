from app.models.tracked_channel_model import TrackedChannel

class TrackedChannelService:
    @staticmethod
    def get_all_channels():
        return TrackedChannel.query.all()
