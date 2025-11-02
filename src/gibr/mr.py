"""GitLab Merge Request operations."""

import logging
import re
import urllib3

import click
import gitlab
from git import Repo

from gibr.notify import error, info, success, warning


def get_project_from_git_remote(remote_name: str = "origin", repo: Repo = None) -> str:
    """Extract GitLab project path from Git remote URL.

    Supports various Git URL formats:
    - SSH: git@gitlab.example.com:group/project.git
    - HTTPS: https://gitlab.example.com/group/project.git
    - SSH with port: ssh://git@gitlab.example.com:2222/group/project.git

    Args:
        remote_name: Name of the remote (default: "origin")
        repo: Git repository object (defaults to current directory)

    Returns:
        str: Project path in format "group/project"

    Raises:
        ValueError: If project path cannot be extracted from remote URL
    """
    try:
        repo = repo or Repo(".")
        remote = repo.remote(name=remote_name)
        remote_url = list(remote.urls)[0]  # Get first URL
        logging.debug(f"Extracting project from remote URL: {remote_url}")

        # Remove .git suffix if present
        remote_url = remote_url.rstrip("/")
        if remote_url.endswith(".git"):
            remote_url = remote_url[:-4]

        # Pattern 1: SSH format (git@host:group/project)
        ssh_pattern = r"git@[^:]+:(.+)$"
        match = re.match(ssh_pattern, remote_url)
        if match:
            project_path = match.group(1)
            logging.debug(f"Extracted project path (SSH format): {project_path}")
            repo.close()
            return project_path

        # Pattern 2: HTTPS format (https://host/group/project)
        https_pattern = r"https?://[^/]+/(.+)$"
        match = re.match(https_pattern, remote_url)
        if match:
            project_path = match.group(1)
            logging.debug(f"Extracted project path (HTTPS format): {project_path}")
            repo.close()
            return project_path

        # Pattern 3: SSH with protocol (ssh://user@host:port/group/project)
        ssh_protocol_pattern = r"ssh://[^@]+@[^/]+/(.+)$"
        match = re.match(ssh_protocol_pattern, remote_url)
        if match:
            project_path = match.group(1)
            logging.debug(f"Extracted project path (SSH protocol format): {project_path}")
            repo.close()
            return project_path

        repo.close()
        raise ValueError(f"Could not extract project path from remote URL: {remote_url}")

    except Exception as e:
        error(f"Failed to get project from git remote: {e}")


class GitLabMR:
    """Handle GitLab Merge Request operations."""

    def __init__(
        self,
        url: str,
        token: str,
        project: str,
        insecure: bool = False,
    ):
        """Initialize GitLab MR handler.

        Args:
            url: GitLab instance URL
            token: GitLab private token
            project: Project path (e.g., 'group/project')
            insecure: Skip SSL certificate verification
        """
        self.url = url
        self.project_name = project
        self.insecure = insecure

        # Disable SSL warnings if insecure mode is enabled
        if insecure:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logging.debug(f"SSL verification disabled for GitLab connection (ssl_verify=False)")

        logging.debug(f"Connecting to GitLab at {url} (insecure={insecure}, ssl_verify={not insecure})")

        try:
            self.client = gitlab.Gitlab(
                url, private_token=token, ssl_verify=not insecure
            )
            logging.debug("GitLab client created, authenticating...")
            self.client.auth()
            logging.debug("GitLab authentication successful")
            self.project = self.client.projects.get(project)
            logging.debug(f"Successfully loaded project: {self.project_name}")
        except Exception as e:
            error(f"Failed to connect to GitLab: {e}")

    def create_merge_request(
        self,
        source_branch: str,
        target_branch: str = None,
        title: str = None,
        description: str = "",
        remove_source_branch: bool = True,
    ) -> dict:
        """Create a merge request in GitLab.

        Args:
            source_branch: Source branch name
            target_branch: Target branch name (defaults to project's default branch)
            title: MR title (defaults to source branch name)
            description: MR description
            remove_source_branch: Whether to remove source branch after merge

        Returns:
            dict: Merge request information
        """
        # Use project default branch if target not specified
        if not target_branch:
            target_branch = self.project.default_branch
            logging.debug(f"Using default target branch: {target_branch}")

        # Use source branch name as title if not provided
        if not title:
            title = source_branch.replace("-", " ").replace("_", " ").title()

        try:
            mr = self.project.mergerequests.create(
                {
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "title": title,
                    "description": description,
                    "remove_source_branch": remove_source_branch,
                }
            )
            return {
                "iid": mr.iid,
                "title": mr.title,
                "web_url": mr.web_url,
                "source_branch": mr.source_branch,
                "target_branch": mr.target_branch,
            }
        except Exception as e:
            error(f"Failed to create merge request: {e}")

    @classmethod
    def from_config(cls, config: dict):
        """Create GitLabMR instance from configuration dictionary.

        Args:
            config: Configuration dictionary with gitlab_mr section

        Returns:
            GitLabMR: Initialized instance
        """
        mr_config = config.get("gitlab_mr", {})
        if not mr_config:
            error(
                "GitLab MR configuration not found. "
                "Please add [gitlab_mr] section to .gibrconfig"
            )

        try:
            url = mr_config["url"]
            token = mr_config["token"]
        except KeyError as e:
            error(f"Missing required configuration in [gitlab_mr]: {e.args[0]}")

        # Get project from config or auto-detect from git remote
        project = mr_config.get("project")
        if not project:
            logging.debug("Project not specified in config, auto-detecting from git remote")
            project = get_project_from_git_remote()
            info(f"Auto-detected project from git remote: {project}")
        else:
            logging.debug(f"Using project from config: {project}")

        # Optional insecure flag (defaults to False)
        # Handle inline comments by splitting on # and taking first part
        insecure_raw = mr_config.get("insecure", "false")
        insecure_str = insecure_raw.split("#")[0].strip().lower()
        insecure = insecure_str in ("true", "yes", "1")
        logging.debug(f"Insecure SSL mode: {insecure} (from config value: '{insecure_raw}' -> parsed: '{insecure_str}')")

        return cls(url=url, token=token, project=project, insecure=insecure)


def push_current_branch(repo: Repo = None, branch_name: str = None) -> tuple[str, str]:
    """Push current branch to origin.

    Args:
        repo: Git repository object (defaults to current directory)
        branch_name: Branch name to push (defaults to current branch)

    Returns:
        tuple: (branch_name, remote_name)
    """
    try:
        repo = repo or Repo(".")

        # Get current branch name
        if not branch_name:
            if repo.head.is_detached:
                error("HEAD is detached. Please checkout a branch first.")
            branch_name = repo.active_branch.name

        logging.debug(f"Current branch: {branch_name}")

        # Check if branch exists on remote
        origin = repo.remote(name="origin")
        remote_refs = [ref.name for ref in origin.refs]
        remote_branch = f"origin/{branch_name}"

        if remote_branch not in remote_refs:
            info(f"Branch '{branch_name}' not found on remote. Pushing...")
            push_result = origin.push(
                refspec=f"{branch_name}:{branch_name}", set_upstream=True
            )
            push_result.raise_if_error()
            success(f"Pushed branch '{branch_name}' to origin.")
        else:
            # Check if local is ahead of remote
            local_commit = repo.head.commit
            remote_commit = origin.refs[branch_name].commit

            if local_commit != remote_commit:
                info(f"Local branch is ahead. Pushing changes...")
                push_result = origin.push(refspec=f"{branch_name}:{branch_name}")
                push_result.raise_if_error()
                success(f"Pushed changes for branch '{branch_name}' to origin.")
            else:
                info(f"Branch '{branch_name}' is up to date with remote.")

        repo.close()
        return branch_name, "origin"

    except Exception as e:
        error(f"Failed to push branch: {e}")

