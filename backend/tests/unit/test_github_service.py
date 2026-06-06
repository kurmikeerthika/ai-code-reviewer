# tests/unit/test_github_service.py
# Tests for GitHubService — URL parsing, markdown formatting.
# These tests do NOT call the real GitHub API.

import pytest
from app.services.github_service import GitHubService


@pytest.fixture
def service():
    return GitHubService()


# ── PR URL Parsing ────────────────────────────────────────────────────────────

class TestParsePRUrl:

    def test_standard_url(self, service):
        owner, repo, number = service.parse_pr_url(
            "https://github.com/owner/repo/pull/42"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert number == 42

    def test_url_with_trailing_slash(self, service):
        owner, repo, number = service.parse_pr_url(
            "https://github.com/octocat/hello-world/pull/1"
        )
        assert owner == "octocat"
        assert repo == "hello-world"
        assert number == 1

    def test_url_with_files_suffix(self, service):
        owner, repo, number = service.parse_pr_url(
            "https://github.com/owner/repo/pull/99/files"
        )
        assert number == 99

    def test_large_pr_number(self, service):
        _, _, number = service.parse_pr_url(
            "https://github.com/owner/repo/pull/12345"
        )
        assert number == 12345

    def test_invalid_url_raises_value_error(self, service):
        with pytest.raises(ValueError) as exc_info:
            service.parse_pr_url("https://github.com/owner/repo")
        assert "Invalid GitHub PR URL" in str(exc_info.value)

    def test_non_github_url_raises(self, service):
        with pytest.raises(ValueError):
            service.parse_pr_url("https://gitlab.com/owner/repo/merge_requests/1")

    def test_empty_string_raises(self, service):
        with pytest.raises(ValueError):
            service.parse_pr_url("")

    def test_repo_with_hyphens_and_dots(self, service):
        owner, repo, number = service.parse_pr_url(
            "https://github.com/my-org/my.repo-name/pull/5"
        )
        assert owner == "my-org"
        assert repo == "my.repo-name"
        assert number == 5


# ── Markdown Formatting ───────────────────────────────────────────────────────

class TestFormatReviewAsMarkdown:

    def make_report(self):
        """Helper: create a minimal valid report dict."""
        return {
            "session_id": "abc123",
            "summary": "The code has several issues that need attention.",
            "statistics": {
                "total_issues": 3,
                "severity_counts": {
                    "critical": 0, "high": 1, "medium": 1, "low": 1, "info": 0
                },
                "by_category": {
                    "bugs": 1, "security": 1, "complexity": 0, "optimization": 1
                },
            },
            "issues": {
                "bugs": [{
                    "issue_id": "BUG_001",
                    "title": "Division by zero",
                    "description": "No zero check before division.",
                    "filename": "main.py",
                    "line_start": 5,
                    "line_end": 6,
                    "code_snippet": "return a / b",
                    "suggestion": "Check if b == 0 first.",
                    "severity": "high",
                    "confidence": 0.95,
                }],
                "security": [{
                    "issue_id": "SEC_001",
                    "title": "Hardcoded password",
                    "description": "Password is stored in plain text.",
                    "filename": "config.py",
                    "line_start": 10,
                    "line_end": 10,
                    "code_snippet": 'password = "admin123"',
                    "suggestion": "Use environment variables.",
                    "severity": "high",
                    "confidence": 0.99,
                }],
                "complexity": [],
                "optimization": [{
                    "issue_id": "OPT_001",
                    "title": "String concatenation in loop",
                    "description": "Use join() instead.",
                    "filename": "utils.py",
                    "line_start": 20,
                    "line_end": 23,
                    "code_snippet": "result += str(item)",
                    "suggestion": "Use ''.join(str(x) for x in data)",
                    "severity": "low",
                    "confidence": 0.85,
                }],
            },
        }

    def test_returns_string(self, service):
        report = self.make_report()
        md = service.format_review_as_markdown(report)
        assert isinstance(md, str)

    def test_contains_title(self, service):
        md = service.format_review_as_markdown(self.make_report())
        assert "AI Code Review Report" in md

    def test_contains_summary(self, service):
        md = service.format_review_as_markdown(self.make_report())
        assert "several issues" in md

    def test_contains_issue_titles(self, service):
        md = service.format_review_as_markdown(self.make_report())
        assert "Division by zero" in md
        assert "Hardcoded password" in md

    def test_contains_session_id(self, service):
        md = service.format_review_as_markdown(self.make_report())
        assert "abc123" in md

    def test_contains_severity_emojis(self, service):
        md = service.format_review_as_markdown(self.make_report())
        assert "🟠" in md  # High severity emoji

    def test_empty_issues_still_renders(self, service):
        report = {
            "session_id": "s1",
            "summary": "All good.",
            "statistics": {
                "total_issues": 0,
                "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
                "by_category": {"bugs": 0, "security": 0, "complexity": 0, "optimization": 0},
            },
            "issues": {"bugs": [], "security": [], "complexity": [], "optimization": []},
        }
        md = service.format_review_as_markdown(report)
        assert isinstance(md, str)
        assert len(md) > 0