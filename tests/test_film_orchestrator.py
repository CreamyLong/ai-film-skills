from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import install_skill
from repository_safety import SafetyError


NAME = "film-production-orchestrator"
LEGACY = "film-production-router"
PACKAGE = ROOT / "skills" / NAME


class OrchestratorContractTests(unittest.TestCase):
    def test_single_canonical_package_and_registry_entry(self):
        data = json.loads((ROOT / "docs/skill-contracts.json").read_text())
        entries = [item for item in data["skills"] if item["name"] in (NAME, LEGACY)]
        self.assertEqual([item["name"] for item in entries], [NAME])
        self.assertEqual(entries[0]["family"], "orchestration")
        self.assertIn("orchestration", data["families"])
        self.assertTrue((PACKAGE / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skills" / LEGACY / "SKILL.md").exists())

    def test_creation_triage_and_direct_stage_modes_are_reachable(self):
        text = (PACKAGE / "SKILL.md").read_text()
        for term in ("name: " + NAME, "Creation orchestration", "Problem triage",
                     "Direct stage request", "references/creation-workflows.md",
                     "references/orchestration-loop.md", "references/routing-cases.md"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_execution_and_blocked_handoff_are_not_just_skill_recommendations(self):
        text = (PACKAGE / "SKILL.md").read_text()
        for term in ("Dispatch ready tasks", "Do not stop at a routing table",
                     "actual host capabilities", "not simulated tool calls",
                     "A finished-film request requires the actual assembled media",
                     "Text-only requests never authorize media generation"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_specialist_ownership_and_real_approvals_are_preserved(self):
        text = (PACKAGE / "SKILL.md").read_text()
        for term in ("specialist roles own", "does not replace their craft",
                     "does not guarantee that the host can switch skills automatically",
                     "user authorizes a change", "never route \"regenerate\" as a fix",
                     "禁止编写或运行批量生成提示词的脚本"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_four_task_paths_have_distinct_preconditions_and_acceptance(self):
        text = (PACKAGE / "references/creation-workflows.md").read_text()
        for term in ("一句话到完整短剧", "参考视频到TVC", "音乐驱动MV", "产品展示片",
                     "90°侧面", "音色", "没有听到", "不编造", "原曲", "产品真值",
                     "Logo", "验收", "逐项"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_loop_tracks_dependencies_versions_stops_and_real_evidence(self):
        text = (PACKAGE / "references/orchestration-loop.md").read_text()
        for term in ("pending", "ready", "running", "review_required", "accepted",
                     "blocked", "stale", "提交结果未知时先对账", "剩余预算",
                     "不创建第二份", "用户批准", "要求看片/试听", "每个镜头"):
            with self.subTest(term=term):
                self.assertIn(term, text)


class OrchestratorInstallationTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/install_skill.py"), *map(str, args)],
            capture_output=True, text=True, timeout=30,
        )

    def test_discovery_and_list_only_expose_canonical_name(self):
        skills = install_skill.discover()
        self.assertIn(NAME, skills)
        self.assertNotIn(LEGACY, skills)
        self.assertEqual(install_skill.SKILL_ALIASES[LEGACY], NAME)
        result = self.run_cli("--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(NAME + "\t", result.stdout)
        self.assertNotIn(LEGACY + "\t", result.stdout)

    def test_old_alias_installs_only_complete_canonical_package(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "installed"
            result = self.run_cli(LEGACY, "--target", target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"{LEGACY} -> {NAME}", result.stderr)
            self.assertFalse((target / LEGACY).exists())
            for source in PACKAGE.rglob("*.md"):
                copy = target / NAME / source.relative_to(PACKAGE)
                self.assertEqual(copy.read_bytes(), source.read_bytes())
            self.assertEqual({p.name for p in target.iterdir()}, {NAME})

    def test_legacy_install_is_not_deleted_even_with_force(self):
        for requested in (NAME, LEGACY):
            with self.subTest(requested=requested), tempfile.TemporaryDirectory() as raw:
                target = Path(raw)
                legacy = target / LEGACY
                legacy.mkdir()
                original = legacy / "SKILL.md"
                original.write_text("user's existing installation")
                result = self.run_cli(requested, "--target", target, "--force")
                self.assertEqual(result.returncode, 1)
                self.assertIn("legacy installation exists", result.stderr)
                self.assertEqual(original.read_text(), "user's existing installation")
                self.assertFalse((target / NAME).exists())

    def test_core_installer_also_rejects_duplicate_legacy_install(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw)
            (target / LEGACY).mkdir()
            with self.assertRaisesRegex(SafetyError, "legacy installation"):
                install_skill.install(PACKAGE, target, force=True)
            self.assertFalse((target / NAME).exists())

    def test_dangling_legacy_symlink_is_not_followed_or_removed(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw)
            link = target / LEGACY
            try:
                link.symlink_to(target / "missing", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            result = self.run_cli(NAME, "--target", target)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(link.is_symlink())
            self.assertFalse((target / NAME).exists())

    def test_existing_canonical_install_still_needs_force(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw)
            self.assertEqual(self.run_cli(NAME, "--target", target).returncode, 0)
            result = self.run_cli(LEGACY, "--target", target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("already exists", result.stderr)
            self.assertTrue((target / NAME / "SKILL.md").is_file())
