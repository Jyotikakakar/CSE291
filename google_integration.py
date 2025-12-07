#!/usr/bin/env python3
"""
Google Calendar and Tasks API Integration.
"""
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import SCOPES


class GoogleIntegration:
    """Handle Google Calendar and Tasks API interactions."""
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.calendar_service = None
        self.tasks_service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Google APIs."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Download from Google Cloud Console: https://console.cloud.google.com/apis/credentials"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        # Build services
        self.calendar_service = build('calendar', 'v3', credentials=creds)
        self.tasks_service = build('tasks', 'v1', credentials=creds)
        
        print("✓ Authenticated with Google Calendar and Tasks")
    
    def create_calendar_event(
        self,
        summary: str,
        description: str = "",
        start_time: datetime = None,
        duration_minutes: int = 60,
        attendees: List[str] = None
    ) -> Optional[Dict]:
        """Create a calendar event."""
        try:
            if start_time is None:
                start_time = datetime.now() + timedelta(days=1)
            
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Los_Angeles',
                },
            }
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            created_event = self.calendar_service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            print(f"✓ Created calendar event: {summary}")
            return created_event
            
        except HttpError as e:
            print(f"Calendar API error: {e}")
            return None
    
    def create_task(
        self,
        title: str,
        notes: str = "",
        due_date: datetime = None,
        task_list_id: str = '@default'
    ) -> Optional[Dict]:
        """Create a task in Google Tasks."""
        try:
            task = {
                'title': title,
                'notes': notes,
            }
            
            if due_date:
                # Google Tasks expects RFC 3339 format for due date (date only, no time)
                task['due'] = due_date.strftime('%Y-%m-%dT00:00:00.000Z')
            
            created_task = self.tasks_service.tasks().insert(
                tasklist=task_list_id,
                body=task
            ).execute()
            
            print(f"✓ Created task: {title}")
            return created_task
            
        except HttpError as e:
            print(f"Tasks API error: {e}")
            return None
    
    def list_task_lists(self) -> List[Dict]:
        """List all task lists."""
        try:
            results = self.tasks_service.tasklists().list().execute()
            return results.get('items', [])
        except HttpError as e:
            print(f"Tasks API error: {e}")
            return []
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """Get upcoming calendar events."""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            max_time = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=max_time,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except HttpError as e:
            print(f"Calendar API error: {e}")
            return []

