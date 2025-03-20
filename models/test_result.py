from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class TestStep:
    name: str
    status: str  # "success", "failure", "error"
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Initialize as empty dict

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "screenshot_path": self.screenshot_path,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class TestResult:
    test_name: str
    youtube_url: str
    format_type: str = "mp4"
    steps: List[TestStep] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    overall_status: str = "pending"
    analysis: Optional[str] = None
    troubleshooting: Optional[str] = None
    video_path: Optional[str] = None

    def add_step(self, step: TestStep):
        self.steps.append(step)

    def complete(self, status: str):
        self.end_time = datetime.now()
        self.overall_status = status

    def to_dict(self):
        return {
            "test_name": self.test_name,
            "youtube_url": self.youtube_url,
            "steps": [step.to_dict() for step in self.steps],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "overall_status": self.overall_status,
            "analysis": self.analysis,
            "troubleshooting": self.troubleshooting,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time
                else None
            ),
        }
