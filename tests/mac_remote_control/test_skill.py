"""Static and offline checks for the mac-remote-control skill."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / 'skills' / 'mac-remote-control'
SCRIPT = SKILL / 'scripts' / 'check-mac-tunnel.sh'
SENSITIVE = ['med_air', 'mac_yzj', '/Users/mac', 'yzj', '/ssd/']


class SkillStructureTest(unittest.TestCase):
    def test_frontmatter_name_matches_directory(self):
        text = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        match = re.match(r'\A---\s*\n(.*?)\n---\n', text, flags=re.S)
        self.assertIsNotNone(match)
        name = re.search(r'^name:\s*(\S+)\s*$', match.group(1), flags=re.M)
        self.assertEqual(name.group(1), 'mac-remote-control')
        self.assertIn('description:', match.group(1))

    def test_required_files_exist(self):
        for rel in ['SKILL.md', 'agents/openai.yaml', 'scripts/check-mac-tunnel.sh', 'references/setup.md']:
            self.assertTrue((SKILL / rel).is_file(), rel)

    def test_no_private_identifiers_in_skill(self):
        for path in SKILL.rglob('*'):
            if path.is_file():
                text = path.read_text(encoding='utf-8')
                for token in SENSITIVE:
                    self.assertNotIn(token, text, f'{path.relative_to(ROOT)} contains {token!r}')


class CheckScriptTest(unittest.TestCase):
    def test_bash_syntax(self):
        subprocess.run(['bash', '-n', str(SCRIPT)], check=True)

    def test_unknown_alias_and_closed_port_fail_without_side_effects(self):
        # 未配置的别名 + 未监听的端口：脚本必须返回非零并给出提示，且不应挂起
        result = subprocess.run(
            ['bash', str(SCRIPT), 'rs-test-nonexistent-alias', '1'],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn('RESULT: FAIL', result.stdout)
        self.assertIn('没有 Host rs-test-nonexistent-alias', result.stdout)


if __name__ == '__main__':
    unittest.main()
