import unittest
import os
import tempfile
import shutil
from unittest.mock import patch
from app.security.validator import validate_user, validate_path
from app.security.rate_limiter import RateLimiter

class TestSecurity(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for sandbox path testing
        self.test_dir = tempfile.mkdtemp()
        self.send_files_path = os.path.realpath(self.test_dir)
        
        # Patch config values for the duration of the test
        self.config_patcher = patch('app.config.config.config.SEND_FILES_PATH', self.send_files_path)
        self.config_patcher.start()
        
        self.user_patcher = patch('app.config.config.config.AUTHORIZED_USERS', {12345, 67890})
        self.user_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        self.user_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_validate_user(self):
        """Test user authorization matching config."""
        self.assertTrue(validate_user(12345))
        self.assertTrue(validate_user(67890))
        self.assertFalse(validate_user(99999))

    def test_validate_path_valid(self):
        """Test that paths inside SEND_FILES are successfully validated."""
        test_file = os.path.join(self.send_files_path, "document.pdf")
        with open(test_file, 'w') as f:
            f.write("dummy")
            
        self.assertTrue(validate_path("document.pdf"))
        
        # Test subdirectories inside sandbox
        nested_dir = os.path.join(self.send_files_path, "subdir")
        os.makedirs(nested_dir, exist_ok=True)
        nested_file = os.path.join(nested_dir, "notes.txt")
        with open(nested_file, 'w') as f:
            f.write("dummy")
            
        self.assertTrue(validate_path("subdir/notes.txt"))

    def test_validate_path_traversal(self):
        """Test that directory traversal attempts are blocked."""
        self.assertFalse(validate_path("../etc/passwd"))
        self.assertFalse(validate_path("../../secret.env"))
        self.assertFalse(validate_path("subdir/../../../outside.txt"))

    def test_validate_path_absolute(self):
        """Test that absolute paths pointing outside are blocked."""
        self.assertFalse(validate_path("/etc/passwd"))
        self.assertFalse(validate_path("/var/log/syslog"))

    def test_validate_path_symlink_escape(self):
        """Test that symlinks pointing outside SEND_FILES are rejected (zero-trust escape protection)."""
        # Create a file outside the sandbox directory
        outside_dir = tempfile.mkdtemp()
        outside_file = os.path.join(outside_dir, "secret.txt")
        with open(outside_file, 'w') as f:
            f.write("secret info")
            
        # Create symlink inside the sandbox pointing to the outside file
        symlink_path = os.path.join(self.send_files_path, "escape_link.txt")
        try:
            os.symlink(outside_file, symlink_path)
            # Should return False because realpath points outside SEND_FILES
            self.assertFalse(validate_path("escape_link.txt"))
        except OSError:
            # Skip if OS does not support symlinks in this environment
            pass
        finally:
            shutil.rmtree(outside_dir)

    def test_validate_path_null_byte(self):
        """Test that null-byte injections are blocked."""
        self.assertFalse(validate_path("document.pdf\x00secret"))

    def test_rate_limiter(self):
        """Test that the rate limiter accurately counts requests and enforces limits."""
        limiter = RateLimiter(limit_per_minute=3)
        user_id = 98765
        
        self.assertTrue(limiter.is_allowed(user_id))
        self.assertTrue(limiter.is_allowed(user_id))
        self.assertTrue(limiter.is_allowed(user_id))
        # 4th command should be denied (limit is 3)
        self.assertFalse(limiter.is_allowed(user_id))

    @patch('app.config.config.config.LARGE_FILE_STRATEGY', 'split')
    def test_large_file_strategy_factory_split(self):
        """Test factory returns SplitStrategy when configured."""
        from app.services.large_file_handler import get_large_file_strategy, SplitStrategy
        strategy = get_large_file_strategy()
        self.assertIsInstance(strategy, SplitStrategy)

    @patch('app.config.config.config.LARGE_FILE_STRATEGY', 'compress')
    def test_large_file_strategy_factory_zip(self):
        """Test factory returns ZipStrategy when configured."""
        from app.services.large_file_handler import get_large_file_strategy, ZipStrategy
        strategy = get_large_file_strategy()
        self.assertIsInstance(strategy, ZipStrategy)

    @patch('app.config.config.config.LARGE_FILE_STRATEGY', 'link')
    def test_large_file_strategy_factory_link(self):
        """Test factory returns LinkStrategy when configured."""
        from app.services.large_file_handler import get_large_file_strategy, LinkStrategy
        strategy = get_large_file_strategy()
        self.assertIsInstance(strategy, LinkStrategy)

    @patch('app.config.config.config.LARGE_FILE_STRATEGY', 'notify')
    def test_large_file_strategy_factory_notify(self):
        """Test factory returns NotifyStrategy when configured."""
        from app.services.large_file_handler import get_large_file_strategy, NotifyStrategy
        strategy = get_large_file_strategy()
        self.assertIsInstance(strategy, NotifyStrategy)

