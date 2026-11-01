import subprocess
import unittest
from pathlib import Path

class TestAudit(unittest.TestCase):
    def test_audit_tool_execution(self):
        script_path = Path("tools/audit_earth_packages.py")
        self.assertTrue(script_path.exists())

        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True
        )

        self.assertIn("Audit fifa_earth", result.stdout)
        self.assertIn("Audit atp_earth", result.stdout)

if __name__ == "__main__":
    unittest.main()
