"""CLI command to create a GitLab merge request."""

import logging
import re

import click

from gibr.factory import get_tracker
from gibr.mr import GitLabMR, push_current_branch
from gibr.notify import info, success, warning
from gibr.translate import auto_translate_if_needed


def extract_issue_id_from_branch(branch_name: str) -> str | None:
    """Extract issue ID from branch name.
    
    Supports formats like:
    - NPDEVOPS-1929-description -> NPDEVOPS-1929
    - FOO-123-some-feature -> FOO-123
    - prefix/PROJ-456/description -> PROJ-456
    
    Args:
        branch_name: Git branch name
        
    Returns:
        Issue ID if found, None otherwise
    """
    # Pattern for Jira-style issue keys (PROJECT-123)
    pattern = r"([A-Z][A-Z0-9_]*-\d+)"
    match = re.search(pattern, branch_name)
    if match:
        return match.group(1)
    return None


@click.command("mr")
@click.option(
    "--target",
    "-t",
    default=None,
    help="Target branch for the merge request (defaults to project's default branch)",
)
@click.option(
    "--title",
    default=None,
    help="Title for the merge request (defaults to source branch name)",
)
@click.option(
    "--description",
    "-d",
    default="",
    help="Description for the merge request",
)
@click.option(
    "--no-push",
    is_flag=True,
    help="Skip pushing the branch to remote (use if already pushed)",
)
@click.option(
    "--keep-source/--remove-source",
    default=None,
    help="Keep or remove source branch after merge (defaults to config or remove)",
)
@click.pass_context
def mr(ctx, target, title, description, no_push, keep_source):
    """Create a GitLab merge request for the current branch."""
    config = ctx.obj["config"]

    # Initialize GitLab MR client from config
    gitlab_mr = GitLabMR.from_config(config.config)
    
    # Determine keep_source behavior: CLI flag > config > default (False)
    if keep_source is None:
        # Check config for default keep_source setting
        mr_config = config.config.get("gitlab_mr", {})
        keep_source_str = mr_config.get("keep_source", "false").split("#")[0].strip().lower()
        keep_source = keep_source_str in ("true", "yes", "1")
        logging.debug(f"Using keep_source from config: {keep_source}")
    else:
        logging.debug(f"Using keep_source from CLI flag: {keep_source}")

    # Push current branch to remote (unless --no-push is specified)
    if not no_push:
        info("Pushing current branch to remote...")
        branch_name, _ = push_current_branch()
    else:
        # Get current branch name without pushing
        from git import Repo

        repo = Repo(".")
        if repo.head.is_detached:
            from gibr.notify import error

            error("HEAD is detached. Please checkout a branch first.")
        branch_name = repo.active_branch.name
        repo.close()
        info(f"Using current branch: {branch_name}")

    # Auto-generate title from issue tracker if not provided
    if not title:
        issue_id = extract_issue_id_from_branch(branch_name)
        if issue_id:
            logging.debug(f"Extracted issue ID from branch: {issue_id}")
            try:
                # Get tracker if configured
                tracker = get_tracker(config.config)
                logging.debug(f"Using tracker: {tracker.__class__.__name__}")
                
                # Fetch issue details
                issue = tracker.get_issue(issue_id)
                
                # Translate title to English if needed
                translated_title = auto_translate_if_needed(issue.title)
                
                # Format as "ISSUE_ID: Translated Title"
                title = f"{issue.id}: {translated_title}"
                info(f"Auto-generated MR title: {title}")
            except Exception as e:
                logging.debug(f"Could not fetch issue details: {e}")
                warning(f"Could not fetch issue {issue_id}, using branch name as title")
                # Fallback to default title generation
                title = None
        else:
            logging.debug("No issue ID found in branch name")

    # Create merge request
    info("Creating merge request...")
    mr_info = gitlab_mr.create_merge_request(
        source_branch=branch_name,
        target_branch=target,
        title=title,
        description=description,
        remove_source_branch=not keep_source,
    )

    # Display success message
    success(
        f"Merge request created: !{mr_info['iid']} - {mr_info['title']}\n"
        f"  Source: {mr_info['source_branch']}\n"
        f"  Target: {mr_info['target_branch']}\n"
        f"  URL: {mr_info['web_url']}"
    )

