from app.models.video_model import Video

class VideoService:
    @staticmethod
    def get_video_by_id(video_id: int):
        return Video.query.get(video_id)
