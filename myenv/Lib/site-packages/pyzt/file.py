from pathlib import Path


# check if file exists
def file_exists(file_path: str) -> bool:
    """Check if file exists
    """
    return Path(file_path).exists()
