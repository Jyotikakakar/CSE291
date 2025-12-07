#!/usr/bin/env python3
"""
Meeting Agent Package
Provides meeting summarization with Google Calendar and Tasks integration.
"""
from config import GEMINI_API_KEY, GEMINI_MODEL, SCOPES
from google_integration import GoogleIntegration
from meeting_agent import MCPMeetingAgent

__all__ = [
    'GEMINI_API_KEY',
    'GEMINI_MODEL',
    'SCOPES',
    'GoogleIntegration',
    'MCPMeetingAgent',
]

