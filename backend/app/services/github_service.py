# app/services/github_service.py
# Handles all GitHub API interactions:
#   - Parsing PR URLs
#   - Fetching PR metadata and changed files
#   - Reading file contents at the PR's head commit
#   - Posting review comments back to the PR

import logging
import re
from typing import List, Dict, Tuple, Optional

from github import Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from app.core.config import settings
from app.core.constants import ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)


class GitHubService:
    """
    Wraps PyGithub to provide a clean interface for PR operations.

    All public methods handle errors gracefully and raise descriptive
    exceptions so the API endpoint can return helpful error messages.
    """

    def __init__(self):
        self._client: Optional[Github] = None

    def _get_client(self) -> Github:
        """
        Lazy initialization of the GitHub client.
        Raises ValueError if GITHUB_TOKEN is not set.
        """
        if self._client is None:
            if not settings.github_token:
                raise ValueError(
                    "GITHUB_TOKEN is not set in your .env file. "
                    "Create a token at https://github.com/settings/tokens "
                    "with 'repo' and 'pull_requests' permissions."
                )
            print("TOKEN FROM SETTINGS =", settings.github_token)
            self._client = Github(settings.github_token)
            logger.info("GitHub client initialized")
        return self._client

    def parse_pr_url(self, pr_url: str) -> Tuple[str, str, int]:
        """
        Extract owner, repo name, and PR number from a GitHub PR URL.

        Supported formats:
            https://github.com/owner/repo/pull/123
            https://github.com/owner/repo/pull/123/files

        Returns:
            Tuple of (owner, repo_name, pr_number)

        Raises:
            ValueError if URL format is not recognized
        """
        # Match standard GitHub PR URL patterns
        pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.search(pattern, pr_url.strip())

        if not match:
            raise ValueError(
                f"Invalid GitHub PR URL: '{pr_url}'. "
                f"Expected format: https://github.com/owner/repo/pull/123"
            )

        owner = match.group(1)
        repo_name = match.group(2)
        pr_number = int(match.group(3))

        logger.info(f"Parsed PR URL: {owner}/{repo_name}#{pr_number}")
        return owner, repo_name, pr_number

    def _get_pr(self, pr_url: str) -> Tuple[Repository, PullRequest]:
        """
        Fetch the Repository and PullRequest objects from GitHub.

        Returns:
            Tuple of (Repository, PullRequest)
        """
        client = self._get_client()
        owner, repo_name, pr_number = self.parse_pr_url(pr_url)
        print("OWNER =", owner)
        print("REPO =", repo_name)
        print("PR NUMBER =", pr_number)
        try:
            repo = client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            logger.info(
                f"Fetched PR: {owner}/{repo_name}#{pr_number} "
                f"— '{pr.title}' ({pr.state})"
            )
            return repo, pr
        except GithubException as e:
            if e.status == 404:
                raise ValueError(
                    f"PR not found: {owner}/{repo_name}#{pr_number}. "
                    f"Check the URL and ensure your token has 'repo' access."
                )
            elif e.status == 401:
                raise ValueError(
                    "GitHub authentication failed. "
                    "Check your GITHUB_TOKEN in .env"
                )
            else:
                raise ValueError(f"GitHub API error: {e.data}")

    def get_pr_metadata(self, pr_url: str) -> Dict:
        """
        Fetch metadata about the PR (title, author, branch, stats).

        Returns a dict with PR information for the review report.
        """
        _, pr = self._get_pr(pr_url)

        return {
            "pr_number": pr.number,
            "title": pr.title,
            "description": pr.body or "",
            "author": pr.user.login,
            "state": pr.state,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "head_sha": pr.head.sha,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "pr_url": pr.html_url,
            "created_at": pr.created_at.isoformat(),
        }

    def fetch_pr_files(
        self,
        pr_url: str,
        max_files: int = 10,
    ) -> Dict[str, str]:
        """
        Fetch the content of all changed files in the PR.

        Filters to only supported code file extensions.
        Skips deleted files (no content to review).
        Skips files larger than 1MB.

        Args:
            pr_url:    Full GitHub PR URL
            max_files: Maximum number of files to fetch

        Returns:
            Dict mapping filename → full file content string
        """
        repo, pr = self._get_pr(pr_url)
        head_sha = pr.head.sha

        file_contents: Dict[str, str] = {}
        skipped: List[str] = []

        try:
            pr_files = list(pr.get_files())
        except GithubException as e:
            raise ValueError(f"Failed to fetch PR files: {e}")

        logger.info(f"PR has {len(pr_files)} changed file(s)")

        for pr_file in pr_files:
            filename = pr_file.filename

            # Skip if file was deleted
            if pr_file.status == "removed":
                logger.debug(f"Skipping deleted file: {filename}")
                skipped.append(f"{filename} (deleted)")
                continue

            # Skip unsupported file types
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                logger.debug(f"Skipping unsupported file type: {filename}")
                skipped.append(f"{filename} (unsupported type)")
                continue

            # Stop if we've hit the file limit
            if len(file_contents) >= max_files:
                logger.warning(
                    f"Reached max_files limit ({max_files}). "
                    f"Skipping remaining files."
                )
                break

            # Fetch file content from GitHub at the PR's head commit
            try:
                content_file = repo.get_contents(filename, ref=head_sha)

                # Skip files larger than 1MB
                if content_file.size > 1_000_000:
                    logger.warning(f"Skipping large file: {filename} ({content_file.size} bytes)")
                    skipped.append(f"{filename} (too large)")
                    continue

                decoded = content_file.decoded_content.decode("utf-8")
                file_contents[filename] = decoded
                logger.info(f"Fetched: {filename} ({len(decoded)} chars)")

            except GithubException as e:
                logger.warning(f"Could not fetch {filename}: {e}")
                skipped.append(f"{filename} (fetch error)")
            except UnicodeDecodeError:
                logger.warning(f"Could not decode {filename} as UTF-8")
                skipped.append(f"{filename} (binary file)")

        if skipped:
            logger.info(f"Skipped files: {skipped}")

        if not file_contents:
            raise ValueError(
                "No reviewable files found in this PR. "
                "The PR may only contain deleted files, binary files, "
                "or unsupported file types."
            )

        logger.info(
            f"Fetched {len(file_contents)} reviewable file(s): "
            f"{list(file_contents.keys())}"
        )

        return file_contents

    def post_review_comment(
        self,
        pr_url: str,
        comment_body: str,
    ) -> str:
        """
        Post a general review comment on the PR (not line-specific).

        This appears in the PR's "Conversation" tab.

        Args:
            pr_url:       GitHub PR URL
            comment_body: Markdown-formatted comment text

        Returns:
            URL of the posted comment
        """
        _, pr = self._get_pr(pr_url)

        try:
            comment = pr.create_issue_comment(comment_body)
            logger.info(f"Posted review comment: {comment.html_url}")
            return comment.html_url
        except GithubException as e:
            raise ValueError(f"Failed to post comment: {e.data}")

    def format_review_as_markdown(self, report: Dict) -> str:
        """
        Convert the AI review report into a well-formatted
        GitHub Markdown comment.

        GitHub renders this with proper headings, tables, and code blocks.
        """
        stats = report.get("statistics", {})
        severity_counts = stats.get("severity_counts", {})
        by_category = stats.get("by_category", {})
        summary = report.get("summary", "No summary available.")
        issues = report.get("issues", {})

        # Severity emoji mapping
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "⚪",
        }

        # Category emoji mapping
        category_emoji = {
            "bugs": "🐛",
            "security": "🔒",
            "complexity": "⏱️",
            "optimization": "💡",
        }

        lines = [
            "# 🤖 AI Code Review Report",
            "",
            f"> **{summary}**",
            "",
            "---",
            "",
            "## 📊 Summary Statistics",
            "",
            f"| Category | Count |",
            f"|----------|-------|",
            f"| 🐛 Bugs | {by_category.get('bugs', 0)} |",
            f"| 🔒 Security | {by_category.get('security', 0)} |",
            f"| ⏱️ Complexity | {by_category.get('complexity', 0)} |",
            f"| 💡 Optimization | {by_category.get('optimization', 0)} |",
            f"| **Total** | **{stats.get('total_issues', 0)}** |",
            "",
            "**Severity Breakdown:**",
        ]

        for sev, count in severity_counts.items():
            if count > 0:
                emoji = severity_emoji.get(sev, "⚪")
                lines.append(f"- {emoji} **{sev.capitalize()}**: {count}")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Output each category's issues
        for category, category_issues in issues.items():
            if not category_issues:
                continue

            emoji = category_emoji.get(category, "📌")
            lines.append(f"## {emoji} {category.capitalize()} Issues")
            lines.append("")

            for issue in category_issues:
                sev = issue.get("severity", "info")
                sev_emoji = severity_emoji.get(sev, "⚪")
                lines.append(
                    f"### {sev_emoji} [{sev.upper()}] {issue.get('title', 'Issue')}"
                )
                lines.append(f"**File:** `{issue.get('filename', 'unknown')}` "
                             f"(lines {issue.get('line_start', '?')}–{issue.get('line_end', '?')})")
                lines.append("")
                lines.append(issue.get("description", ""))
                lines.append("")

                snippet = issue.get("code_snippet", "")
                if snippet:
                    lines.append("**Problematic code:**")
                    lines.append(f"```")
                    lines.append(snippet)
                    lines.append(f"```")
                    lines.append("")

                suggestion = issue.get("suggestion", "")
                if suggestion:
                    lines.append(f"**Suggestion:** {suggestion}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        lines.append(
            "*Generated by [AI Code Reviewer](https://github.com) "
            f"— Session: `{report.get('session_id', 'unknown')}`*"
        )

        return "\n".join(lines)


# Shared singleton
github_service = GitHubService()