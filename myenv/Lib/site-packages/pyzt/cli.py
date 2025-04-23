import typer
from pyzt.folder import get_files, get_folders
from typing import Optional

app = typer.Typer()


@app.command()
def cli_get_files(from_folder: str, extension: Optional[str] = ""):
    """Get all files of type (extension - string or regex string) from a directory"""
    result = get_files(from_folder, extension)
    typer.echo(result)


@app.command()
def cli_get_folders(from_folder: Optional[str] = "./", exclude: Optional[str] = ""):
    """Get all folders from current folder, with an optional regex string to exclude folders"""
    result = get_folders(from_folder, exclude)
    typer.echo(result)


if __name__ == "__main__":
    app()
