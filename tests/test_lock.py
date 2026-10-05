import unittest
from unittest.mock import patch, MagicMock
from app.security.lock_detector import LockDetectorManager

class TestLockDetector(unittest.TestCase):
    
    @patch('app.security.lock_detector.GnomeLockDetector.is_locked')
    @patch('app.security.lock_detector.LogindLockDetector.is_locked')
    @patch('os.getenv')
    def test_lock_manager_locked_by_gnome(self, mock_getenv, mock_logind_locked, mock_gnome_locked):
        """Test that LockDetectorManager reports locked if GNOME detector reports locked."""
        mock_getenv.return_value = "ubuntu:GNOME"
        mock_gnome_locked.return_value = True
        mock_logind_locked.return_value = False
        
        # Patch other detectors to avoid making real DBus calls
        with patch('app.security.lock_detector.KdeLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.CinnamonLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.MateLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.XfceLockDetector.is_locked', return_value=False):
            
            manager = LockDetectorManager()
            self.assertTrue(manager.is_locked())
        
    @patch('app.security.lock_detector.GnomeLockDetector.is_locked')
    @patch('app.security.lock_detector.LogindLockDetector.is_locked')
    @patch('os.getenv')
    def test_lock_manager_unlocked(self, mock_getenv, mock_logind_locked, mock_gnome_locked):
        """Test that LockDetectorManager reports unlocked if all detectors report unlocked."""
        mock_getenv.return_value = "ubuntu:GNOME"
        mock_gnome_locked.return_value = False
        mock_logind_locked.return_value = False
        
        with patch('app.security.lock_detector.KdeLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.CinnamonLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.MateLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.XfceLockDetector.is_locked', return_value=False):
                 
            manager = LockDetectorManager()
            self.assertFalse(manager.is_locked())

    @patch('app.security.lock_detector.LogindLockDetector.is_locked')
    @patch('os.getenv')
    def test_lock_manager_locked_by_logind_fallback(self, mock_getenv, mock_logind_locked):
        """Test that LockDetectorManager falls back to logind and reports locked if logind says so."""
        mock_getenv.return_value = ""  # Unknown desktop DE
        mock_logind_locked.return_value = True
        
        with patch('app.security.lock_detector.GnomeLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.KdeLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.CinnamonLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.MateLockDetector.is_locked', return_value=False), \
             patch('app.security.lock_detector.XfceLockDetector.is_locked', return_value=False):
                 
            manager = LockDetectorManager()
            self.assertTrue(manager.is_locked())
