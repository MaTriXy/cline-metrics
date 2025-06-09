#!/usr/bin/env python3
"""
Cline Session Analysis Tool
Analyzes time allocation between memory bank work and actual development
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import platform

@dataclass
class SessionMetrics:
    """Metrics for a single Cline session"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: float
    memory_bank_time: float
    task_management_time: float
    project_code_time: float
    config_time: float
    tool_time: float
    total_file_edits: int
    memory_bank_files: List[str]
    project_files: List[str]

class ClineSessionAnalyzer:
    def __init__(self, sessions_path: str):
        self.sessions_path = Path(sessions_path)
        self.sessions: List[SessionMetrics] = []
        
    def categorize_file_path(self, file_path: str) -> str:
        """Categorize a file path into memory bank, task management, config, or project code"""
        file_path_lower = file_path.lower()
        filename = Path(file_path).name.lower()
        
        # Task management: TASK files, _index.md, or files in tasks/ directories
        if (filename.startswith('task') and filename.endswith('.md')) or \
           filename == '_index.md' or \
           '/tasks/' in file_path_lower:
            return 'task_management'
        elif 'memory-bank' in file_path_lower:
            return 'memory_bank'
        elif any(config in file_path_lower for config in ['cline_mcp_settings.json', '.clinerules', '.env', 'pyproject.toml']):
            return 'config'
        elif any(ext in file_path_lower for ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.css', '.html', '.sql', '.yaml', '.yml']):
            return 'project_code'
        else:
            return 'other'
    
    def analyze_session_timing(self, ui_messages: List[Dict]) -> Dict[str, float]:
        """Analyze time spent in different categories based on UI messages"""
        category_times = defaultdict(float)
        
        for i, message in enumerate(ui_messages):
            if message.get('type') != 'say' or message.get('say') != 'tool':
                continue
                
            timestamp = message.get('ts', 0)
            tool_text = message.get('text', '')
            
            # Extract file path from tool usage
            file_path = None
            if '"path":' in tool_text:
                # Extract path from JSON-like tool text
                try:
                    # Simple regex to extract path
                    path_match = re.search(r'"path":\s*"([^"]+)"', tool_text)
                    if path_match:
                        file_path = path_match.group(1)
                except:
                    pass
            
            if not file_path:
                continue
                
            # Calculate time until next message
            duration = 0
            if i + 1 < len(ui_messages):
                next_timestamp = ui_messages[i + 1].get('ts', timestamp)
                duration = (next_timestamp - timestamp) / 1000.0  # Convert to seconds
            
            # Categorize and add time
            category = self.categorize_file_path(file_path)
            if category != 'other':
                category_times[category] += duration
                
        return dict(category_times)
    
    def parse_session(self, session_dir: Path) -> Optional[SessionMetrics]:
        """Parse a single session directory"""
        try:
            session_id = session_dir.name
            
            # Read UI messages
            ui_messages_file = session_dir / 'ui_messages.json'
            if not ui_messages_file.exists():
                return None
                
            with open(ui_messages_file, 'r') as f:
                ui_messages = json.load(f)
            
            if not ui_messages:
                return None
            
            # Get session timing
            start_time = datetime.fromtimestamp(ui_messages[0]['ts'] / 1000.0)
            end_time = datetime.fromtimestamp(ui_messages[-1]['ts'] / 1000.0) if ui_messages else start_time
            duration_minutes = (end_time - start_time).total_seconds() / 60.0
            
            # Analyze time allocation
            category_times = self.analyze_session_timing(ui_messages)
            
            # Count file operations
            memory_bank_files = []
            project_files = []
            total_edits = 0
            
            for message in ui_messages:
                if message.get('type') == 'say' and message.get('say') == 'tool':
                    tool_text = message.get('text', '')
                    if any(action in tool_text for action in ['editedExistingFile', 'createdNewFile']):
                        total_edits += 1
                        
                        # Extract file path
                        path_match = re.search(r'"path":\s*"([^"]+)"', tool_text)
                        if path_match:
                            file_path = path_match.group(1)
                            category = self.categorize_file_path(file_path)
                            if category == 'memory_bank':
                                memory_bank_files.append(file_path)
                            elif category == 'project_code':
                                project_files.append(file_path)
            
            return SessionMetrics(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                memory_bank_time=category_times.get('memory_bank', 0) / 60.0,  # Convert to minutes
                task_management_time=category_times.get('task_management', 0) / 60.0,
                project_code_time=category_times.get('project_code', 0) / 60.0,
                config_time=category_times.get('config', 0) / 60.0,
                tool_time=sum(category_times.values()) / 60.0,
                total_file_edits=total_edits,
                memory_bank_files=memory_bank_files,
                project_files=project_files
            )
            
        except Exception as e:
            print(f"Error parsing session {session_dir.name}: {e}")
            return None
    
    def analyze_all_sessions(self, limit: Optional[int] = None) -> None:
        """Analyze all sessions in the directory"""
        if not self.sessions_path.exists():
            print(f"Sessions path does not exist: {self.sessions_path}")
            return
        
        session_dirs = [d for d in self.sessions_path.iterdir() if d.is_dir()]
        session_dirs.sort(key=lambda x: x.name, reverse=True)  # Most recent first
        
        if limit:
            session_dirs = session_dirs[:limit]
        
        print(f"Analyzing {len(session_dirs)} sessions...")
        
        for session_dir in session_dirs:
            metrics = self.parse_session(session_dir)
            if metrics and metrics.duration_minutes > 1:  # Only include sessions > 1 minute
                self.sessions.append(metrics)
        
        print(f"Successfully parsed {len(self.sessions)} sessions")
    
    def generate_report(self) -> None:
        """Generate analysis report"""
        if not self.sessions:
            print("No sessions to analyze!")
            return
        
        # Calculate totals
        total_duration = sum(s.duration_minutes for s in self.sessions)
        total_memory_bank = sum(s.memory_bank_time for s in self.sessions)
        total_task_mgmt = sum(s.task_management_time for s in self.sessions)
        total_project_code = sum(s.project_code_time for s in self.sessions)
        total_config = sum(s.config_time for s in self.sessions)
        total_tool_time = sum(s.tool_time for s in self.sessions)
        
        print("\n" + "="*60)
        print("📊 CLINE SESSION ANALYSIS REPORT")
        print("="*60)
        
        print(f"\n📈 OVERALL STATISTICS")
        print(f"Total Sessions Analyzed: {len(self.sessions)}")
        print(f"Total Time Spent: {total_duration:.1f} minutes ({total_duration/60:.1f} hours)")
        print(f"Average Session Length: {total_duration/len(self.sessions):.1f} minutes")
        
        print(f"\n⏰ TIME ALLOCATION BREAKDOWN")
        if total_tool_time > 0:
            memory_bank_pct = (total_memory_bank / total_tool_time) * 100
            task_mgmt_pct = (total_task_mgmt / total_tool_time) * 100
            project_code_pct = (total_project_code / total_tool_time) * 100
            config_pct = (total_config / total_tool_time) * 100
            
            print(f"Memory Bank Work:     {total_memory_bank:.1f}m ({memory_bank_pct:.1f}%)")
            print(f"Task Management:      {total_task_mgmt:.1f}m ({task_mgmt_pct:.1f}%)")
            print(f"Project Code:         {total_project_code:.1f}m ({project_code_pct:.1f}%)")
            print(f"Configuration:        {total_config:.1f}m ({config_pct:.1f}%)")
            print(f"Total Tracked Time:   {total_tool_time:.1f}m")
            
            # Key insight
            overhead_time = total_memory_bank + total_task_mgmt + total_config
            overhead_pct = (overhead_time / total_tool_time) * 100
            
            print(f"\n🎯 KEY INSIGHTS")
            print(f"Memory Bank Investment: {memory_bank_pct:.1f}% of tracked time")
            print(f"Total Overhead (Memory Bank + Tasks + Config): {overhead_pct:.1f}%")
            print(f"Actual Development Time: {project_code_pct:.1f}%")
            print(f"Development Efficiency Ratio: {project_code_pct/overhead_pct:.2f}:1" if overhead_pct > 0 else "N/A")
        
        # File activity analysis
        all_memory_bank_files = []
        all_project_files = []
        
        for session in self.sessions:
            all_memory_bank_files.extend(session.memory_bank_files)
            all_project_files.extend(session.project_files)
        
        if all_memory_bank_files:
            print(f"\n📁 MEMORY BANK FILE ACTIVITY")
            memory_bank_counter = Counter(Path(f).name for f in all_memory_bank_files)
            for filename, count in memory_bank_counter.most_common(5):
                print(f"  {filename}: {count} edits")
        
        # Recent trends
        print(f"\n📅 RECENT SESSION TRENDS (Last 10 sessions)")
        recent_sessions = self.sessions[:10]
        for session in recent_sessions:
            if session.tool_time > 0:
                mb_pct = (session.memory_bank_time / session.tool_time) * 100
                code_pct = (session.project_code_time / session.tool_time) * 100
                date_str = session.start_time.strftime("%m/%d %H:%M")
                print(f"  {date_str}: Memory Bank {mb_pct:.0f}%, Code {code_pct:.0f}% ({session.duration_minutes:.0f}m)")

def get_default_cline_path():
    """Get the default Cline sessions path based on the operating system"""
    system = platform.system()
    home = Path.home()
    
    if system == "Darwin":  # macOS
        return home / "Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks"
    elif system == "Windows":
        return home / "AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/tasks"
    elif system == "Linux":
        return home / ".config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks"
    else:
        # Fallback - try common paths
        paths = [
            home / ".config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks",
            home / "AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/tasks",
            home / "Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks"
        ]
        for path in paths:
            if path.exists():
                return path
        return paths[0]  # Return first path as fallback


def main():
    parser = argparse.ArgumentParser(description="Analyze Cline session data for time allocation metrics")
    parser.add_argument(
        "--path", 
        type=str, 
        default=None,
        help="Custom path to Cline sessions directory (auto-detected if not provided)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=None,
        help="Limit analysis to the N most recent sessions"
    )
    
    args = parser.parse_args()
    
    # Use provided path or auto-detect
    if args.path:
        sessions_path = Path(args.path)
    else:
        sessions_path = get_default_cline_path()
    
    print(f"🔍 Searching for Cline sessions at: {sessions_path}")
    
    if not sessions_path.exists():
        print(f"❌ Path does not exist: {sessions_path}")
        print("\n💡 To specify a custom path, use:")
        print(f"   python {sys.argv[0]} --path /your/custom/path")
        print("\n🔍 Common Cline session locations:")
        print("   macOS:   ~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks")
        print("   Windows: ~/AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/tasks")
        print("   Linux:   ~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks")
        sys.exit(1)
    
    analyzer = ClineSessionAnalyzer(str(sessions_path))
    analyzer.analyze_all_sessions(limit=args.limit)
    analyzer.generate_report()

if __name__ == "__main__":
    main()
