# Cline Session Analysis Tool

Analyze your Cline session data to understand time allocation between memory bank work, task management, and actual development.

## Features

- **Cross-platform**: Works on macOS, Windows, and Linux
- **Auto-detection**: Automatically finds your Cline sessions directory
- **Detailed metrics**: Time breakdown by category with efficiency ratios
- **File activity tracking**: See which memory bank files you edit most
- **Recent trends**: Track your recent session patterns

## Usage

### Basic Usage (Auto-detect path)
```bash
python analyze_cline_sessions.py
```

### Custom Path
```bash
python analyze_cline_sessions.py --path "/your/custom/path/to/cline/sessions"
```

### Analyze Only Recent Sessions
```bash
python analyze_cline_sessions.py --limit 50
```

### Help
```bash
python analyze_cline_sessions.py --help
```

## Default Cline Session Locations

- **macOS**: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks`
- **Windows**: `~/AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/tasks`  
- **Linux**: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks`

## Sample Output

```
📊 CLINE SESSION ANALYSIS REPORT
============================================================

📈 OVERALL STATISTICS
Total Sessions Analyzed: 434
Total Time Spent: 2304.5 hours
Average Session Length: 318.6 minutes

⏰ TIME ALLOCATION BREAKDOWN
Memory Bank Work:     150.4m (10.6%)
Task Management:      177.3m (12.5%)
Project Code:         1053.3m (74.4%)
Configuration:        35.0m (2.5%)

🎯 KEY INSIGHTS
Memory Bank Investment: 10.6% of tracked time
Total Overhead (Memory Bank + Tasks + Config): 25.6%
Actual Development Time: 74.4%
Development Efficiency Ratio: 2.90:1
```

## Requirements

- Python 3.8+
- No external dependencies (uses only standard library)

## Categories

- **Memory Bank Work**: Files in `memory-bank/` directories (activeContext.md, progress.md, etc.)
- **Task Management**: Task files (TASK*.md), _index.md, and files in tasks/ directories
- **Project Code**: Source code files (.py, .js, .ts, .css, .html, etc.)
- **Configuration**: Cline settings, .clinerules, environment files

## License

Free to use and share!
