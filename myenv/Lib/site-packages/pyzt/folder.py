from pathlib import Path
import re


# get all files (from a directory) of type (extension string such as ".txt", or also can be a regex string
def get_files(from_folder: Path | str, extension: str | None = "") -> list[str]:
    """Get all files of type (extension - string or regex string) from a directory
    """
    if isinstance(from_folder, str):
        from_folder = Path(from_folder)

    if re.match(r"^\.[a-zA-Z0-9]+$", extension):
        return [str(file) for file in from_folder.glob(f"*{extension}")]
    else:
        return [
            str(file) for file in from_folder.glob("*")
            if re.match(extension, file.name)
        ]


# get all folders from given folder, with an optional regex string to exclude folders
def get_folders(from_folder: Path | str, exclude: str | None = "") -> list[str]:
    """Get all folders from current folder, with an optional regex string to exclude folders
    """
    if isinstance(from_folder, str):
        from_folder = Path(from_folder)

    if exclude:
        return [
            str(folder) for folder in from_folder.iterdir()
            if folder.is_dir() and not re.match(exclude, folder.name)
        ]
    else:
        return [str(folder) for folder in from_folder.iterdir() if folder.is_dir()]
