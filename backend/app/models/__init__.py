"""Models package – imports all ORM models so Base.metadata is fully populated
and re-exports every name for backward-compatible ``from app.models import X`` usage."""

# New models
from app.models.ai_conversation import AIConversation, AIMessage, MessageRole
from app.models.device_command import CommandStatus, DeviceCommand
from app.models.device_event import DeviceEvent, DeviceEventType
from app.models.device_type import DeviceCategory, DeviceType
from app.models.game_mode import GameMode
from app.models.player import Player
from app.models.system_setting import SystemSetting
from app.models.user import Role, User, user_role_assignments

# Existing models (updated)
from app.models.device import Device, DeviceStatus
from app.models.game_result import GameResult, ResultWinner
from app.models.game_session import GameSession
from app.models.mission import Mission, MissionObjective, MissionStatus
from app.models.prop import Prop, PropType
from app.models.schedule import ScheduleItem
from app.models.score_event import ScoreEvent
from app.models.system_log import LogCategory, LogLevel, SystemLog
from app.models.team import Team, TeamSide
from app.models.user_role import UserRole  # legacy CRUD table kept for backward compat

__all__ = [
    # New
    "AIConversation",
    "AIMessage",
    "MessageRole",
    "CommandStatus",
    "DeviceCommand",
    "DeviceEvent",
    "DeviceEventType",
    "DeviceCategory",
    "DeviceType",
    "GameMode",
    "Player",
    "SystemSetting",
    "Role",
    "User",
    "user_role_assignments",
    # Existing (updated)
    "Device",
    "DeviceStatus",
    "GameResult",
    "ResultWinner",
    "GameSession",
    "Mission",
    "MissionObjective",
    "MissionStatus",
    "Prop",
    "PropType",
    "ScheduleItem",
    "ScoreEvent",
    "LogCategory",
    "LogLevel",
    "SystemLog",
    "Team",
    "TeamSide",
    # Legacy
    "UserRole",
]

