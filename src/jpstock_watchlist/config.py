"""Application configuration settings."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Application default paths and configurations."""

    input_dir: Path = Path("input")
    output_dir: Path = Path("output")
    jpx400_file: Path = Path("input/screener_result.csv")


settings = Settings()
