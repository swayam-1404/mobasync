import os
import subprocess
import logging
import dbus

logger = logging.getLogger(__name__)

class BaseLockDetector:
    """Base class for all lock status detectors."""
    
    def is_locked(self) -> bool:
        """Return True if locked, False if unlocked."""
        raise NotImplementedError("Subclasses must implement is_locked()")

class GnomeLockDetector(BaseLockDetector):
    """Detect lock status for GNOME desktop via DBus."""
    
    def is_locked(self) -> bool:
        try:
            bus = dbus.SessionBus()
            obj = bus.get_object('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver')
            interface = dbus.Interface(obj, 'org.gnome.ScreenSaver')
            # GetActive returns 1 if locked, 0 if unlocked
            return bool(interface.GetActive())
        except dbus.DBusException as e:
            logger.debug(f"GNOME ScreenSaver check failed (normal if not running GNOME): {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error in GNOME lock detector: {e}")
            return False

class KdeLockDetector(BaseLockDetector):
    """Detect lock status for KDE desktop via DBus."""
    
    def is_locked(self) -> bool:
        try:
            bus = dbus.SessionBus()
            obj = bus.get_object('org.freedesktop.ScreenSaver', '/ScreenSaver')
            interface = dbus.Interface(obj, 'org.freedesktop.ScreenSaver')
            # GetActive returns True if locked, False if unlocked
            return bool(interface.GetActive())
        except dbus.DBusException as e:
            logger.debug(f"KDE ScreenSaver check failed (normal if not running KDE): {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error in KDE lock detector: {e}")
            return False

class CinnamonLockDetector(BaseLockDetector):
    """Detect lock status for Cinnamon desktop via DBus."""
    
    def is_locked(self) -> bool:
        try:
            bus = dbus.SessionBus()
            obj = bus.get_object('org.cinnamon.ScreenSaver', '/org/cinnamon/ScreenSaver')
            interface = dbus.Interface(obj, 'org.cinnamon.ScreenSaver')
            return bool(interface.GetActive())
        except dbus.DBusException as e:
            logger.debug(f"Cinnamon ScreenSaver check failed: {e}")
            return False

class MateLockDetector(BaseLockDetector):
    """Detect lock status for MATE desktop via DBus."""
    
    def is_locked(self) -> bool:
        try:
            bus = dbus.SessionBus()
            obj = bus.get_object('org.mate.ScreenSaver', '/org/mate/ScreenSaver')
            interface = dbus.Interface(obj, 'org.mate.ScreenSaver')
            return bool(interface.GetActive())
        except dbus.DBusException as e:
            logger.debug(f"MATE ScreenSaver check failed: {e}")
            return False

class XfceLockDetector(BaseLockDetector):
    """Detect lock status for XFCE desktop via DBus or xscreensaver."""
    
    def is_locked(self) -> bool:
        try:
            bus = dbus.SessionBus()
            obj = bus.get_object('org.xfce.ScreenSaver', '/org/xfce/ScreenSaver')
            interface = dbus.Interface(obj, 'org.xfce.ScreenSaver')
            return bool(interface.GetActive())
        except dbus.DBusException:
            pass
            
        # Fallback to xscreensaver CLI
        try:
            res = subprocess.run(
                ['xscreensaver-command', '-time'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1
            )
            if res.returncode == 0 and "locked" in res.stdout.lower():
                return True
        except Exception:
            pass
            
        return False

class LogindLockDetector(BaseLockDetector):
    """Detect lock status using systemd-logind via System DBus."""
    
    def is_locked(self) -> bool:
        try:
            uid = os.getuid()
            bus = dbus.SystemBus()
            manager_obj = bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1')
            manager = dbus.Interface(manager_obj, 'org.freedesktop.login1.Manager')
            
            sessions = manager.ListSessions()
            graphical_sessions_locked = []
            
            for session_id, s_uid, username, seat, obj_path in sessions:
                if s_uid == uid:
                    session_obj = bus.get_object('org.freedesktop.login1', obj_path)
                    props = dbus.Interface(session_obj, 'org.freedesktop.DBus.Properties')
                    
                    s_type = str(props.Get('org.freedesktop.login1.Session', 'Type'))
                    s_class = str(props.Get('org.freedesktop.login1.Session', 'Class'))
                    s_active = bool(props.Get('org.freedesktop.login1.Session', 'Active'))
                    
                    # We only audit active/graphical user sessions
                    if s_class == "user" and s_type in ("wayland", "x11"):
                        try:
                            locked_hint = bool(props.Get('org.freedesktop.login1.Session', 'LockedHint'))
                            # Session is locked if LockedHint is True OR if session is not active
                            graphical_sessions_locked.append(locked_hint or not s_active)
                        except dbus.DBusException:
                            # Fallback if LockedHint property is missing
                            graphical_sessions_locked.append(not s_active)
            
            # Zero-trust: If no graphical user session exists, treat as locked/blocked
            if not graphical_sessions_locked:
                return True
                
            # If all graphical sessions are locked or inactive, then screen is locked
            return all(graphical_sessions_locked)
        except Exception as e:
            logger.debug(f"logind lock detector failed: {e}")
            # If systemd check fails, return False to let session DBus detectors decide
            return False

class LockDetectorManager:
    """Manages and executes all lock detectors in a priority/fallback order."""
    
    def __init__(self):
        self.detectors = [
            GnomeLockDetector(),
            KdeLockDetector(),
            CinnamonLockDetector(),
            MateLockDetector(),
            XfceLockDetector(),
            LogindLockDetector()
        ]
        
    def is_locked(self) -> bool:
        """
        Check if the desktop is currently locked.
        Zero-trust: If ANY active detector claims the desktop is locked, returns True.
        """
        desktop = os.getenv("XDG_CURRENT_DESKTOP", "").upper()
        
        # 1. Prioritize current desktop environment check
        if "GNOME" in desktop:
            if GnomeLockDetector().is_locked():
                return True
        elif "KDE" in desktop:
            if KdeLockDetector().is_locked():
                return True
        elif "XFCE" in desktop:
            if XfceLockDetector().is_locked():
                return True
        elif "CINNAMON" in desktop:
            if CinnamonLockDetector().is_locked():
                return True
        elif "MATE" in desktop:
            if MateLockDetector().is_locked():
                return True
                
        # 2. Check systemd-logind (highly reliable system wide)
        if LogindLockDetector().is_locked():
            return True
            
        # 3. Fallback: query all detectors; if any reports locked, return True
        for detector in self.detectors:
            try:
                if detector.is_locked():
                    return True
            except Exception as e:
                logger.debug(f"Lock detector {detector.__class__.__name__} errored: {e}")
                
        return False

# Singleton manager
lock_detector = LockDetectorManager()
