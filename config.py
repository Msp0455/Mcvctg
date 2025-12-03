import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"

class AudioQuality(str, Enum):
    LOW = "64k"
    MEDIUM = "128k"
    HIGH = "192k"
    VERY_HIGH = "320k"
    
    @classmethod
    def from_string(cls, value: str):
        """Convert string to AudioQuality enum"""
        value = value.upper()
        if value == "LOW":
            return cls.LOW
        elif value == "MEDIUM":
            return cls.MEDIUM
        elif value == "HIGH":
            return cls.HIGH
        elif value == "VERY_HIGH":
            return cls.VERY_HIGH
        elif value in ["64k", "128k", "192k", "320k"]:
            # Direct bitrate values
            return cls(value)
        else:
            # Default to HIGH
            return cls.HIGH

@dataclass
class AudioConfig:
    quality: AudioQuality = field(
        default_factory=lambda: AudioQuality.from_string(
            os.getenv("AUDIO_QUALITY", "HIGH")
        )
    )
    format: str = field(default_factory=lambda: os.getenv("AUDIO_FORMAT", "mp3"))
    bitrate: str = field(default_factory=lambda: os.getenv("AUDIO_BITRATE", "192k"))
    sample_rate: int = field(default_factory=lambda: int(os.getenv("AUDIO_SAMPLE_RATE", 44100)))
    max_file_size: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", 52428800)))  # 50MB
    buffer_size: int = field(default_factory=lambda: int(os.getenv("BUFFER_SIZE", 4096)))
