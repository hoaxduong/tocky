import uuid

import oss2


class OSSClient:
    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        bucket_name: str,
    ):
        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)

    def upload_audio(
        self,
        consultation_id: uuid.UUID,
        sequence: int,
        audio_bytes: bytes,
    ) -> str:
        oss_key = f"audio/{consultation_id}/{sequence:06d}.pcm"
        self.bucket.put_object(oss_key, audio_bytes)
        return oss_key

    def get_audio_url(self, oss_key: str, expires: int = 3600) -> str:
        return self.bucket.sign_url("GET", oss_key, expires)
