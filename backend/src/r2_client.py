import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger("r2_client")

class R2Client:
    def __init__(self):
        self.account_id = os.environ.get("R2_ACCOUNT_ID", "")
        self.access_key_id = os.environ.get("R2_ACCESS_KEY_ID", "")
        self.secret_access_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
        self.bucket_name = os.environ.get("R2_BUCKET_NAME", "clipviral-videos")
        self._s3_client = None

    @property
    def s3_client(self):
        if self._s3_client is None:
            if not self.account_id or not self.access_key_id or not self.secret_access_key:
                raise ValueError(
                    "Cloudflare R2 credentials (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY) "
                    "must be configured in environment variables to use storage operations."
                )
            endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
            self._s3_client = boto3.client(
                service_name="s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name="auto",
                config=Config(signature_version="s3v4")
            )
        return self._s3_client

    def generate_presigned_put_url(self, key: str, content_type: str, expires_in: int = 3600) -> str:
        """
        Generates a pre-signed URL for direct browser-to-R2 upload using PUT.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": content_type
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned PUT URL: {e}")
            raise RuntimeError(f"Could not generate presigned upload URL: {e}")

    def download_file(self, key: str) -> bytes:
        """
        Downloads a file from the R2 bucket.
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading file {key} from R2: {e}")
            raise RuntimeError(f"Could not download file from R2: {e}")

    def upload_file_data(self, key: str, data: bytes, content_type: str = "video/mp4"):
        """
        Uploads raw file bytes to R2.
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type
            )
        except ClientError as e:
            logger.error(f"Error uploading file {key} to R2: {e}")
            raise RuntimeError(f"Could not upload file to R2: {e}")
