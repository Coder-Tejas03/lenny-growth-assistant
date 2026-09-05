"""Lenny Growth Assistant — Phase 1 Scaffold & Implementation Contract Gate Tests.

Verifies that the repository skeleton, security hygiene, environment configurations,
Docker Compose definitions, and the 16 architectural implementation contract items
are fully established and compliant before progressing to Phase 2.
"""

import os
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestPhase1SecurityAndGitHygiene(unittest.TestCase):
    """Verifies repository tracking hygiene and secret prevention rules."""

    def test_git_repository_initialized(self):
        """Asserts git repository is initialized."""
        git_dir = REPO_ROOT / ".git"
        self.assertTrue(git_dir.exists() and git_dir.is_dir(), ".git directory must exist.")

    def test_gitignore_covers_critical_targets(self):
        """Asserts .gitignore blocks secrets, caches, and database volumes."""
        gitignore_path = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore must exist in root.")
        content = gitignore_path.read_text()

        critical_patterns = [
            ".env",
            "__pycache__/",
            "node_modules/",
            "postgres_data/",
            "!.env.example",
            "!.gitkeep",
        ]
        for pattern in critical_patterns:
            self.assertIn(pattern, content, f"Pattern '{pattern}' missing from .gitignore")

    def test_no_live_env_file_tracked(self):
        """Asserts no real .env file is tracked in git."""
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "", "A live .env file is tracked in Git!")


class TestPhase1ConfigurationTemplate(unittest.TestCase):
    """Verifies .env.example contains required parameters and safe placeholders."""

    def test_env_example_contains_all_variables(self):
        """Asserts all expected service, model, budget, and retrieval variables exist."""
        env_example_path = REPO_ROOT / ".env.example"
        self.assertTrue(env_example_path.exists(), ".env.example must exist in root.")
        content = env_example_path.read_text()

        required_keys = [
            "DATABASE_URL",
            "DATABASE_URL_SYNC",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "AGENT_RUNTIME=pi",
            "DEFAULT_LLM_PROVIDER=openai",
            "OPENAI_API_KEY",
            "OPENAI_MODEL=gpt-4o-mini",
            "OPENAI_BUDGET_USD=4.00",
            "OPENAI_EMBEDDING_MODEL=text-embedding-3-small",
            "EMBEDDING_DIMENSION=1536",
            "OLLAMA_BASE_URL",
            "OLLAMA_MODEL=qwen2.5:1.5b",
            "RETRIEVAL_TOP_K=5",
            "RETRIEVAL_SIMILARITY_THRESHOLD=0.65",
            "NEXT_PUBLIC_API_URL",
        ]
        for key in required_keys:
            self.assertIn(key, content, f"Required configuration '{key}' missing from .env.example")

    def test_env_example_has_no_real_secrets(self):
        """Asserts no real OpenAI key is present in .env.example."""
        content = (REPO_ROOT / ".env.example").read_text()
        self.assertFalse(re.search(r"sk-[a-zA-Z0-9]{20,}", content), "Potential real OpenAI key in .env.example!")
        self.assertIn("OPENAI_API_KEY=your_openai_api_key_here", content)


class TestPhase1DockerCompose(unittest.TestCase):
    """Verifies Docker Compose orchestration definition."""

    def test_docker_compose_config_valid(self):
        """Asserts docker compose config executes with exit code 0."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"docker compose config failed: {result.stderr}")
        output = result.stdout

        self.assertIn("lenny_postgres", output, "db service missing from docker-compose.yml")
        self.assertIn("lenny_backend", output, "backend service missing from docker-compose.yml")
        self.assertIn("lenny_frontend", output, "frontend service missing from docker-compose.yml")
        self.assertIn("postgres_data", output, "postgres_data volume missing from docker-compose.yml")


class TestPhase1DirectoryLayout(unittest.TestCase):
    """Verifies the presence of required directory layout and service files."""

    def test_required_directories_exist(self):
        """Asserts all modular workspaces exist."""
        required_dirs = [
            "backend/app",
            "backend/tests",
            "frontend/src",
            "agent-runtime/src",
            "ingestion",
            "tests/unit",
            "tests/integration",
            "tests/evaluation",
            "docs",
            "agent_transcripts",
        ]
        for rel_dir in required_dirs:
            target = REPO_ROOT / rel_dir
            self.assertTrue(target.exists() and target.is_dir(), f"Directory {rel_dir} does not exist.")

    def test_service_manifests_exist(self):
        """Asserts manifests for Python, Node runtime, and frontend exist."""
        self.assertTrue((REPO_ROOT / "backend/requirements.txt").exists())
        self.assertTrue((REPO_ROOT / "backend/Dockerfile").exists())
        self.assertTrue((REPO_ROOT / "agent-runtime/package.json").exists())
        self.assertTrue((REPO_ROOT / "agent-runtime/tsconfig.json").exists())
        self.assertTrue((REPO_ROOT / "frontend/package.json").exists())
        self.assertTrue((REPO_ROOT / "frontend/Dockerfile").exists())


class TestPhase1ImplementationContract(unittest.TestCase):
    """Verifies all 16 items of Section 30 of architecture.md are in docs/implementation-contract.md."""

    def test_implementation_contract_sections_complete(self):
        contract_path = REPO_ROOT / "docs/implementation-contract.md"
        self.assertTrue(contract_path.exists(), "docs/implementation-contract.md must exist.")
        content = contract_path.read_text()

        contract_requirements = [
            ("PostgreSQL Schema", "CREATE TABLE users"),
            ("Sessions Table", "CREATE TABLE sessions"),
            ("Messages Table", "CREATE TABLE messages"),
            ("Episodes Table", "CREATE TABLE episodes"),
            ("Transcript Chunks Table", "CREATE TABLE transcript_chunks"),
            ("Message Citations Table", "CREATE TABLE message_citations"),
            ("Artifacts Table", "CREATE TABLE artifacts"),
            ("Chunking Strategy", "500 to 800 tokens"),
            ("Embedding Dimension", "vector(1536)"),
            ("HNSW Parameters", "m = 16, ef_construction = 64"),
            ("Similarity Formula", "1 - (c.embedding <=> :query_embedding::vector)"),
            ("Retrieval Threshold", "0.65"),
            ("Citation Contract", "[Episode: Guest Name, Timestamp/Topic]"),
            ("Skill Routing", "grounded_qa"),
            ("Ship30 Skill", "ship30_writer"),
            ("Artifact Skill", "artifact_generator"),
            ("SSE Streaming", "text/event-stream"),
            ("Artifact Sandbox", 'sandbox="allow-scripts"'),
            ("Forbidden Origin", "allow-same-origin"),
            ("Evaluation Accuracy Metric", "90%"),
            ("Hosted Topology", "Vercel"),
        ]

        for label, snippet in contract_requirements:
            self.assertIn(snippet, content, f"Section for '{label}' (searching for '{snippet}') missing in implementation contract!")


if __name__ == "__main__":
    unittest.main()
