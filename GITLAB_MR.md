# GitLab Merge Request Feature

## Overview
This feature allows you to create GitLab merge requests directly from the command line, with support for self-hosted GitLab instances and insecure SSL connections.

## Files Created/Modified

### New Files
1. **`src/gibr/mr.py`** - Core GitLab MR functionality
   - `GitLabMR` class for handling merge request operations
   - Support for insecure SSL connections (self-signed certificates)
   - `push_current_branch()` utility function

2. **`src/gibr/cli/mr.py`** - CLI command for creating MRs
   - Command: `gibr mr`
   - Options: `--target`, `--title`, `--description`, `--no-push`, `--keep-source`

3. **`.gibrconfig.example`** - Example configuration file
   - Shows how to configure the `[gitlab_mr]` section

### Modified Files
1. **`src/gibr/cli/__init__.py`**
   - Registered the new `mr` command
   - Updated to skip tracker loading for the `mr` command (since it works independently)

2. **`README.md`**
   - Added documentation for the `gibr mr` command
   - Added configuration examples

## Configuration

Add the following section to your `.gibrconfig`:

```ini
[gitlab_mr]
url = https://gitlab.example.com
# project is optional - auto-detected from git remote URL if not specified
# project = group/project-name
token = ${GITLAB_TOKEN}
insecure = false  # Set to true for self-hosted instances with self-signed certificates
keep_source = false  # Set to true to keep source branch after merge by default
```

**Required parameters:**
- `url` — GitLab instance URL
- `token` — GitLab personal access token

**Optional parameters:**
- `project` — Project path (e.g., `group/project-name`). If not specified, automatically extracted from git remote URL
- `insecure` — Set to `true` for self-signed SSL certificates (default: `false`)
- `keep_source` — Set to `true` to keep the source branch after merge by default (default: `false`)

### Auto-detection from Git Remote

The `project` parameter is now optional. If not specified in the configuration, it will be automatically extracted from your git remote URL. Supported formats:

- **SSH**: `git@gitlab.stage.stage:d.ovsianikov/testing.git` → `d.ovsianikov/testing`
- **HTTPS**: `https://gitlab.example.com/group/project.git` → `group/project`
- **SSH with port**: `ssh://git@gitlab.example.com:2222/group/project.git` → `group/project`

## Usage Examples

### Basic Usage
```bash
# Create MR with defaults (auto-pushes branch, targets default branch)
gibr mr
```

### Advanced Usage
```bash
# Create MR with custom target branch and title
gibr mr --target main --title "Add new feature"

# Create MR with description
gibr mr --description "This MR implements feature X"

# Skip pushing (if branch is already on remote)
gibr mr --no-push

# Keep source branch after merge
gibr mr --keep-source

# Explicitly remove source branch after merge (overrides config)
gibr mr --remove-source
```

## Features

### Core Functionality
- ✅ Create merge requests from current branch
- ✅ Automatic branch pushing to remote
- ✅ Support for self-hosted GitLab instances
- ✅ Insecure SSL connections (for self-signed certificates)
- ✅ Auto-detect project from git remote URL (SSH, HTTPS, and SSH with port)
- ✅ Configurable target branch (defaults to project's default branch)
- ✅ Configurable title and description
- ✅ Option to keep or remove source branch after merge (CLI flags or config default)

### Architecture
- **Separate from issue trackers**: The MR functionality is independent of the issue tracker configuration
- **Configuration-driven**: All GitLab settings are stored in `.gibrconfig`
- **SSL verification**: Can be disabled for self-hosted instances with `insecure = true`
- **Smart project detection**: Automatically extracts project path from git remote URL if not specified in config

## Dependencies
- `python-gitlab>=6.5.0` (already in project dependencies)
- `urllib3` (dependency of python-gitlab)

## Implementation Details

### Project Auto-detection
The `get_project_from_git_remote()` function extracts the project path from the git remote URL:
1. Fetches the remote URL from the specified remote (default: "origin")
2. Removes `.git` suffix if present
3. Tries to match against three URL patterns:
   - SSH format: `git@gitlab.example.com:group/project.git`
   - HTTPS format: `https://gitlab.example.com/group/project.git`
   - SSH with protocol: `ssh://git@gitlab.example.com:2222/group/project.git`
4. Returns the extracted project path (e.g., `group/project`)

This makes the `project` configuration parameter optional, improving user experience.

### SSL Certificate Verification
When `insecure = true` is set in the configuration:
1. SSL warnings are suppressed using `urllib3.disable_warnings()`
2. GitLab client is initialized with `ssl_verify=False`
3. Appropriate logging is added for debugging

### Branch Management
The `push_current_branch()` function:
1. Checks if the branch exists on remote
2. If not, pushes with `--set-upstream`
3. If yes, checks if local is ahead and pushes if needed
4. Returns the branch name and remote name

### Error Handling
- Validates GitLab connection during initialization
- Provides clear error messages for missing configuration
- Handles Git command errors gracefully
- Checks for detached HEAD state before proceeding

## Testing
As requested, no tests were written for this feature.

## Future Enhancements (Not Implemented)
- Interactive mode for selecting target branch
- Draft MR creation
- Assignee and reviewer assignment
- Label and milestone management
- MR template support

