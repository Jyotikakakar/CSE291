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
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
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
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
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
    
    def get_events_on_date(self, target_date: datetime) -> List[Dict]:
        """Get all events on a specific date."""
        try:
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except HttpError as e:
            print(f"Calendar API error: {e}")
            return []
    
    def check_conflict(self, start_time: datetime, duration_minutes: int = 60) -> bool:
        """Check if there's a conflict at the given time slot."""
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=start_time.isoformat() + '-08:00',
                timeMax=end_time.isoformat() + '-08:00',
                singleEvents=True
            ).execute()
            
            events = events_result.get('items', [])
            return len(events) > 0
            
        except HttpError as e:
            print(f"Calendar API error checking conflict: {e}")
            return False
    
    def find_free_slot(
        self, 
        target_date: datetime, 
        duration_minutes: int = 60,
        start_hour: int = 9,
        end_hour: int = 17
    ) -> Optional[datetime]:
        """Find a free time slot on the given date between start_hour and end_hour."""
        try:
            events = self.get_events_on_date(target_date)
            busy_periods = []
            for event in events:
                start = event['start'].get('dateTime')
                end = event['end'].get('dateTime')
                if start and end:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    busy_periods.append((
                        start_dt.replace(tzinfo=None),
                        end_dt.replace(tzinfo=None)
                    ))
            
            busy_periods.sort(key=lambda x: x[0])
            current_date = target_date.date()
            
            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:
                    slot_start = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                    slot_end = slot_start + timedelta(minutes=duration_minutes)
                    
                    if slot_end.hour > end_hour or (slot_end.hour == end_hour and slot_end.minute > 0):
                        continue
                    
                    is_free = True
                    for busy_start, busy_end in busy_periods:
                        if not (slot_end <= busy_start or slot_start >= busy_end):
                            is_free = False
                            break
                    
                    if is_free:
                        return slot_start
            
            return None
            
        except Exception as e:
            print(f"Error finding free slot: {e}")
            return None
    
    def create_calendar_event_smart(
        self,
        summary: str,
        description: str = "",
        preferred_time: datetime = None,
        duration_minutes: int = 60,
        attendees: List[str] = None
    ) -> Optional[Dict]:
        """
        Create a calendar event with smart conflict resolution.
        If the preferred time has a conflict, finds an alternative slot on the same day.
        """
        if preferred_time is None:
            preferred_time = datetime.now() + timedelta(days=1)
        
        if self.check_conflict(preferred_time, duration_minutes):
            print(f"⚠ Conflict detected at {preferred_time.strftime('%Y-%m-%d %H:%M')}, finding alternative...")
            
            alternative_time = self.find_free_slot(
                preferred_time,
                duration_minutes,
                start_hour=9,
                end_hour=18
            )
            
            if alternative_time:
                print(f"✓ Found free slot at {alternative_time.strftime('%H:%M')}")
                preferred_time = alternative_time
            else:
                next_day = preferred_time + timedelta(days=1)
                alternative_time = self.find_free_slot(
                    next_day,
                    duration_minutes,
                    start_hour=9,
                    end_hour=18
                )
                if alternative_time:
                    print(f"✓ No slots today, scheduled for {alternative_time.strftime('%Y-%m-%d %H:%M')}")
                    preferred_time = alternative_time
                else:
                    print("⚠ Could not find free slot, scheduling anyway (may conflict)")
        
        return self.create_calendar_event(
            summary=summary,
            description=description,
            start_time=preferred_time,
            duration_minutes=duration_minutes,
            attendees=attendees
        )
    
    def delete_task(self, task_id: str, task_list_id: str = '@default') -> bool:
        """Delete a task by ID."""
        try:
            self.tasks_service.tasks().delete(
                tasklist=task_list_id,
                task=task_id
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                return True
            print(f"Error deleting task {task_id}: {e}")
            return False
    
    def delete_calendar_event(self, event_id: str) -> bool:
        """Delete a calendar event by ID."""
        try:
            self.calendar_service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status in [404, 410]:
                return True
            print(f"Error deleting event {event_id}: {e}")
            return False
    
    def delete_multiple_tasks(self, task_ids: List[str], task_list_id: str = '@default') -> int:
        """Delete multiple tasks. Returns count of successfully deleted."""
        deleted = 0
        for task_id in task_ids:
            if self.delete_task(task_id, task_list_id):
                deleted += 1
        return deleted
    
    def delete_multiple_events(self, event_ids: List[str]) -> int:
        """Delete multiple calendar events. Returns count of successfully deleted."""
        deleted = 0
        for event_id in event_ids:
            if self.delete_calendar_event(event_id):
                deleted += 1
        return deleted

