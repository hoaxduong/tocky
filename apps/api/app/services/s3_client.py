"""S3-compatible storage client.

Drop-in replacement for OSSClient — same interface, works with any
S3-compatible provider (Cloudflare R2, AWS S3, MinIO, Backblaze B2, etc.).
"""

import uuid

import boto3


class S3Client:
    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        access_key_secret: str,
        bucket_name: str,
        region: str = "auto",
        public_url: str = "",
    ):
        self.bucket_name = bucket_name
        self.public_url = public_url.rstrip("/")
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret,
            region_name=region,
        )

    def upload_audio(
        self,
        consultation_id: uuid.UUID,
        sequence: int,
        audio_bytes: bytes,
    ) -> str:
        key = f"audio/{consultation_id}/{sequence:06d}.pcm"
        self.s3.put_object(Bucket=self.bucket_name, Key=key, Body=audio_bytes)
        return key

    def get_audio_url(self, oss_key: str, expires: int = 3600) -> str:
        if self.public_url:
            return f"{self.public_url}/{oss_key}"
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": oss_key},
            ExpiresIn=expires,
        )

    def download_object(self, oss_key: str) -> bytes:
        resp = self.s3.get_object(Bucket=self.bucket_name, Key=oss_key)
        return resp["Body"].read()

    def upload_full_audio(
        self,
        consultation_id: uuid.UUID,
        audio_bytes: bytes,
        extension: str = "wav",
    ) -> str:
        key = f"audio/{consultation_id}/full.{extension}"
        self.s3.put_object(Bucket=self.bucket_name, Key=key, Body=audio_bytes)
        return key

    def upload_pcm(
        self,
        consultation_id: uuid.UUID,
        pcm_bytes: bytes,
    ) -> str:
        key = f"audio/{consultation_id}/source.pcm"
        self.s3.put_object(Bucket=self.bucket_name, Key=key, Body=pcm_bytes)
        return key
