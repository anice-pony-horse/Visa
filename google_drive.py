"""
Google Drive Handler - Integration with Google Drive API
Handles authentication, file listing, and downloads
"""

import os
import io
import json
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import tempfile


class GoogleDriveHandler:
    """Handle Google Drive operations"""

    def __init__(self, credentials_file=None):
        """
        Initialize Google Drive handler

        Args:
            credentials_file: Path to service account JSON or uploaded file object
        """
        self.service = None
        self.temp_dir = tempfile.gettempdir()

        if credentials_file:
            self._authenticate(credentials_file)

    def _authenticate(self, credentials_file):
        """Authenticate with Google Drive API"""
        try:
            # Handle both file paths and uploaded file objects
            if hasattr(credentials_file, 'read'):
                # It's an uploaded file object
                creds_dict = json.loads(credentials_file.read())
            else:
                # It's a file path
                with open(credentials_file, 'r') as f:
                    creds_dict = json.load(f)

            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )

            # Build service
            self.service = build('drive', 'v3', credentials=credentials)
            print("✅ Google Drive authenticated successfully")

        except Exception as e:
            print(f"❌ Error authenticating with Google Drive: {e}")
            raise

    def extract_folder_id(self, folder_url: str) -> str:
        """
        Extract folder ID from Google Drive URL

        Args:
            folder_url: Full Google Drive folder URL

        Returns:
            Folder ID
        """
        # Handle different URL formats
        if '/folders/' in folder_url:
            return folder_url.split('/folders/')[-1].split('?')[0]
        elif 'id=' in folder_url:
            return folder_url.split('id=')[-1].split('&')[0]
        else:
            # Assume it's already just the ID
            return folder_url

    def list_folder_files(self, folder_url: str, file_types: Optional[List[str]] = None) -> List[Dict]:
        """
        List all files in a Google Drive folder

        Args:
            folder_url: Google Drive folder URL or ID
            file_types: Optional list of MIME types to filter

        Returns:
            List of file dictionaries with id, name, mimeType
        """
        if not self.service:
            raise Exception("Not authenticated with Google Drive")

        folder_id = self.extract_folder_id(folder_url)

        # Default to PDF and common document types
        if file_types is None:
            file_types = [
                'application/pdf',
                'application/vnd.google-apps.document',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'image/jpeg',
                'image/png'
            ]

        files = []

        try:
            # Query for files in folder
            query = f"'{folder_id}' in parents and trashed=false"

            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, createdTime)",
                pageSize=1000
            ).execute()

            items = results.get('files', [])

            # Filter by file type if specified
            for item in items:
                if not file_types or item['mimeType'] in file_types:
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'mimeType': item['mimeType'],
                        'size': item.get('size', 0),
                        'createdTime': item.get('createdTime')
                    })

            print(f"✅ Found {len(files)} files in folder")
            return files

        except Exception as e:
            print(f"❌ Error listing folder files: {e}")
            raise

    def list_folder_recursive(self, folder_url: str, file_types: Optional[List[str]] = None) -> List[Dict]:
        """
        Recursively list all files in folder and subfolders

        Args:
            folder_url: Google Drive folder URL or ID
            file_types: Optional list of MIME types to filter

        Returns:
            List of all files in folder tree
        """
        if not self.service:
            raise Exception("Not authenticated with Google Drive")

        folder_id = self.extract_folder_id(folder_url)
        all_files = []

        def _recurse_folder(folder_id: str, path: str = ""):
            """Recursively get files from folder"""
            try:
                # Get all items in current folder
                query = f"'{folder_id}' in parents and trashed=false"
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name, mimeType, size, createdTime)",
                    pageSize=1000
                ).execute()

                items = results.get('files', [])

                for item in items:
                    # If it's a folder, recurse into it
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        subfolder_path = f"{path}/{item['name']}" if path else item['name']
                        _recurse_folder(item['id'], subfolder_path)
                    else:
                        # It's a file
                        if not file_types or item['mimeType'] in file_types:
                            file_info = {
                                'id': item['id'],
                                'name': item['name'],
                                'mimeType': item['mimeType'],
                                'size': item.get('size', 0),
                                'createdTime': item.get('createdTime'),
                                'path': f"{path}/{item['name']}" if path else item['name']
                            }
                            all_files.append(file_info)

            except Exception as e:
                print(f"Error processing folder {folder_id}: {e}")

        # Start recursion
        _recurse_folder(folder_id)

        print(f"✅ Found {len(all_files)} files in folder tree")
        return all_files

    def download_file(self, file_id: str, file_name: str) -> str:
        """
        Download a file from Google Drive

        Args:
            file_id: Google Drive file ID
            file_name: Name for the downloaded file

        Returns:
            Path to downloaded file
        """
        if not self.service:
            raise Exception("Not authenticated with Google Drive")

        try:
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            mime_type = file_metadata['mimeType']

            # Handle Google Docs (need to export)
            if mime_type.startswith('application/vnd.google-apps'):
                if 'document' in mime_type:
                    # Export as PDF
                    request = self.service.files().export_media(
                        fileId=file_id,
                        mimeType='application/pdf'
                    )
                    file_name = file_name.replace('.gdoc', '.pdf')
                else:
                    raise Exception(f"Unsupported Google Apps type: {mime_type}")
            else:
                # Regular file download
                request = self.service.files().get_media(fileId=file_id)

            # Download to temp directory
            file_path = os.path.join(self.temp_dir, file_name)

            with io.FileIO(file_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            print(f"✅ Downloaded: {file_name}")
            return file_path

        except Exception as e:
            print(f"❌ Error downloading file {file_name}: {e}")
            raise

    def download_folder(self, folder_url: str, recursive: bool = True) -> List[Dict]:
        """
        Download entire folder from Google Drive

        Args:
            folder_url: Google Drive folder URL or ID
            recursive: Whether to include subfolders

        Returns:
            List of downloaded file information
        """
        # Get file list
        if recursive:
            files = self.list_folder_recursive(folder_url)
        else:
            files = self.list_folder_files(folder_url)

        downloaded_files = []

        # Download each file
        for file_info in files:
            try:
                file_path = self.download_file(file_info['id'], file_info['name'])
                downloaded_files.append({
                    **file_info,
                    'local_path': file_path
                })
            except Exception as e:
                print(f"Failed to download {file_info['name']}: {e}")

        return downloaded_files
