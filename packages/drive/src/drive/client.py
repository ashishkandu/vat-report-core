import io
import re
from pathlib import Path

from googleapiclient.discovery import Resource
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from shared.logger import LoggerFactory

from .models import GoogleDriveFile, GoogleDriveFileList

# from .caching import cache_it

logger = LoggerFactory.get_logger(__name__)


class GDriveClient:
    def __init__(self, service: Resource):
        self.service = service
        logger.info("GDriveClient initialized.")

    def list_files(
        self,
        page_size: int,
        mime_type: str | None = None,
        parent_folder_id: str
        | None = None,  # NEW: Added parent_folder_id for targeted listing
    ) -> GoogleDriveFileList:
        """Lists files from Google Drive, optionally filtered by MIME type and parent folder."""
        logger.info(
            "Listing files from Google Drive (parent: %s)...",
            parent_folder_id if parent_folder_id else "root",
        )

        query_parts = ["trashed=false"]  # Only list non-trashed files
        if mime_type:
            query_parts.append(f"mimeType='{mime_type}'")
        if parent_folder_id:
            query_parts.append(
                f"'{parent_folder_id}' in parents",
            )  # Files specifically in this folder

        query = " and ".join(query_parts)

        try:
            response = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    fields="kind, files(id, name, mimeType, kind, modifiedTime)",
                )
                .execute()
            )
            return GoogleDriveFileList(**response)
        except Exception as e:
            logger.exception("Error listing Google Drive files.")
            msg = f"Failed to list Google Drive files: {e}"
            raise RuntimeError(msg) from e

    def find_latest_file(
        self,
        page_size: int,
        file_pattern: str,
    ) -> GoogleDriveFile | None:
        """
        Retrieve the latest file from Google Drive that matches the specified pattern.

        Args:
            page_size (int): The maximum number of files to retrieve from Google Drive.
            file_pattern (str): The regular expression pattern used to match file names in Google Drive.

        Returns:
            GoogleDriveFile | None: The metadata of the latest matching file, or None if no file is found.

        """
        logger.info("Retrieving the latest file by pattern: %s", file_pattern)

        query = "trashed=false"

        try:
            response = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    orderBy="modifiedTime desc",
                    fields="kind, files(id, name, mimeType, kind, modifiedTime)",
                )
                .execute()
            )
        except Exception as e:
            logger.exception("Error finding latest file in Google Drive.")
            msg = f"Failed to find latest Google Drive file: {e}"
            raise RuntimeError(msg) from e

        files = GoogleDriveFileList(**response)

        # Validate the file pattern
        try:
            compiled_pattern = re.compile(file_pattern)
        except re.error as e:
            logger.exception("Invalid regular expression pattern: '%s'", file_pattern)
            msg = f"Invalid file pattern: {e}"
            raise ValueError(msg) from e

        # Filter files by the specified pattern
        matching_items = [
            file for file in files.files if compiled_pattern.search(file.name)
        ]

        if not matching_items:
            logger.info("No file matching the pattern '%s' found.", file_pattern)
            return None

        logger.debug("Total matching files: %s / %s", len(matching_items), page_size)

        return matching_items[0]

    def download_file(self, file: GoogleDriveFile, destination: Path) -> Path:
        """
        Downloads a file to the specified directory.

        This method assumes the caller has already determined if a download is necessary.

        Args:
            file (GoogleDriveFile): The file to be downloaded from Google Drive.
            destination (Path): The directory where the file will be saved.

        Returns:
            Path: The path to the downloaded file.

        Raises:
            RuntimeError: If there's an error during download or file writing.

        """
        file_path = destination / file.name

        # Ensure the destination directory exists
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.exception("Could not create directory for file download.")
            msg = f"Failed to create directory {file_path.parent}: {e}"
            raise RuntimeError(msg) from e

        logger.info("Starting download of '%s' to '%s'...", file.name, file_path)
        request = self.service.files().get_media(fileId=file.id)

        if file_path.exists():
            logger.warning("File already exists at %s, overwriting.", file_path)
            try:
                file_path.unlink()  # Ensure clean overwrite
            except OSError as e:
                logger.exception("Could not remove existing file")
                msg = f"Could not remove existing file {file_path}: {e}"
                raise RuntimeError(msg) from e

        fd = io.BytesIO()
        downloader = MediaIoBaseDownload(fd, request, chunksize=1024 * 1024)
        done = False
        total_size_mb = 0  # To store total size for final log
        while not done:
            status, done = downloader.next_chunk()
            if status.total_size:  # Avoid division by zero if total_size is 0 initially
                total_size_mb = status.total_size / (1024 * 1024)
                logger.info(
                    "Downloaded %d%% of %.2f MB",
                    int(status.progress() * 100),
                    total_size_mb,
                )
            else:
                logger.info(
                    "Downloaded %d%%",
                    int(status.progress() * 100),
                )  # If total_size not available yet

        try:
            file_path.write_bytes(fd.getvalue())
            logger.info("File write complete: %s", file_path)
        except OSError as e:
            logger.exception("Error writing downloaded file to disk.")
            msg = f"Failed to write file {file.name} to {file_path}: {e}"
            raise RuntimeError(msg) from e

        # cache_it(drive_file)

        return file_path

    def get_folder_id(
        self,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> str | None:
        """
        Finds a folder by name within a specified parent folder or at root.

        Returns the folder ID if found, otherwise None.
        """
        logger.debug(
            "Searching for folder '%s' in parent '%s'...",
            folder_name,
            parent_folder_id if parent_folder_id else "root",
        )
        query_parts = [
            f"name='{folder_name}'",
            "mimeType='application/vnd.google-apps.folder'",
            "trashed=false",
        ]
        if parent_folder_id:
            query_parts.append(f"'{parent_folder_id}' in parents")
        else:
            # If no parent, search in root folders (not in any specific folder)
            # This query is tricky; a simpler approach is to list all and filter,
            # but 'in parents' clause is better for hierarchy.
            # For truly root folders, no 'in parents' clause is needed for default listing.
            pass  # No specific parent query if parent_folder_id is None

        query = " and ".join(query_parts)

        try:
            response = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=10,  # We usually expect unique folder names within a parent
                    fields="files(id, name)",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )

            files = response.get("files", [])
            if files:
                logger.debug(
                    "Folder '%s' found with ID: %s",
                    folder_name,
                    files[0]["id"],
                )
                return files[0]["id"]

            logger.debug("Folder '%s' not found.", folder_name)
        except Exception as e:
            logger.exception("Error searching for folder '%s'.", folder_name)
            msg = f"Failed to find folder '{folder_name}': {e}"
            raise RuntimeError(msg) from e
        else:
            return None

    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> str:
        """
        Creates a new folder in Google Drive.

        Returns the ID of the newly created folder.
        """
        logger.info(
            "Creating folder '%s' (parent: %s)...",
            folder_name,
            parent_folder_id if parent_folder_id else "root",
        )
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        try:
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
            folder_id = file.get("id")
            logger.info("Folder '%s' created with ID: %s", folder_name, folder_id)
        except Exception as e:
            logger.exception("Error creating folder '%s'.", folder_name)
            msg = f"Failed to create folder '{folder_name}': {e}"
            raise RuntimeError(msg) from e
        else:
            return folder_id

    def get_or_create_folder(
        self,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> str:
        """
        Attempts to find a folder by name; if not found, creates it.

        Returns the ID of the existing or newly created folder.
        """
        folder_id = self.get_folder_id(folder_name, parent_folder_id)
        if folder_id:
            return folder_id

        return self.create_folder(folder_name, parent_folder_id)

    def upload_file(
        self,
        file_name: str,
        file_buffer: io.BytesIO,
        mime_type: str,
        parent_folder_id: str | None = None,
    ) -> GoogleDriveFile:
        """Uploads a file (from an in-memory BytesIO buffer) to Google Drive."""
        logger.info(
            "Uploading file '%s' (MIME: %s) to folder '%s'...",
            file_name,
            mime_type,
            parent_folder_id if parent_folder_id else "root",
        )

        file_metadata = {
            "name": file_name,
            "mimeType": mime_type,
        }
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        media = MediaIoBaseUpload(file_buffer, mimetype=mime_type, resumable=True)

        try:
            # Check if a file with the same name already exists in the target folder
            # This is to avoid duplicates, or to allow overwriting if desired.
            existing_file_id = None
            existing_files_response = (
                self.service.files()
                .list(
                    q=f"name='{file_name}' and '{parent_folder_id}' in parents and trashed=false",
                    fields="files(id, name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            existing_files = existing_files_response.get("files", [])

            if existing_files:
                existing_file_id = existing_files[0]["id"]
                logger.warning(
                    "File '%s' already exists in folder %s. Overwriting (updating existing file)...",
                    file_name,
                    parent_folder_id,
                )
                # If updating an existing file, use files().update()
                request = self.service.files().update(
                    fileId=existing_file_id,
                    media_body=media,
                    fields="id, name, mimeType, modifiedTime",
                    supportsAllDrives=True,
                )
            else:
                # If creating a new file, use files().create()
                logger.debug(
                    "Creating new file '%s' in folder %s.",
                    file_name,
                    parent_folder_id,
                )
                request = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, mimeType, modifiedTime",
                    supportsAllDrives=True,
                )

            # Execute the upload/update
            response_file = request.execute()
            logger.info(
                "File '%s' uploaded/updated successfully (ID: %s).",
                response_file.get("name"),
                response_file.get("id"),
            )
            return GoogleDriveFile(**response_file)

        except Exception as e:
            logger.exception("Error uploading file '%s' to Google Drive.", file_name)
            msg = f"Failed to upload file '{file_name}': {e}"
            raise RuntimeError(msg) from e
