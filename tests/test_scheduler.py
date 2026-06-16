"""
Tests for Ansible scheduler module.
"""
import pytest
import yaml
import os

SCHEDULER_DIR = "ansible/roles/redguard-scheduler"

class TestAnsibleRoleStructure:
    def test_role_has_tasks(self):
        assert os.path.exists(f"{SCHEDULER_DIR}/tasks/main.yml")

    def test_role_has_defaults(self):
        assert os.path.exists(f"{SCHEDULER_DIR}/defaults/main.yml")

    def test_role_has_templates(self):
        assert os.path.exists(f"{SCHEDULER_DIR}/templates")

    def test_tasks_are_valid_yaml(self):
        with open(f"{SCHEDULER_DIR}/tasks/main.yml") as f:
            data = yaml.safe_load(f)
            assert data is not None

    def test_defaults_are_valid_yaml(self):
        with open(f"{SCHEDULER_DIR}/defaults/main.yml") as f:
            data = yaml.safe_load(f)
            assert data is not None
            assert "rg_scan_types" in data

    def test_playbook_exists(self):
        assert os.path.exists("ansible/playbooks/schedule.yml")

    def test_playbook_is_valid_yaml(self):
        with open("ansible/playbooks/schedule.yml") as f:
            data = yaml.safe_load(f)
            assert data is not None
            assert len(data) > 0
