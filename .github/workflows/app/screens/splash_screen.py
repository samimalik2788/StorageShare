"""
StorageShare - Splash Screen
Displays "Love Pakistan" on app startup
"""

from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.lang import Builder
import os

# Load KV file
kv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kv', 'splash.kv')
Builder.load_file(kv_path)


class SplashScreen(Screen):
    """Splash screen showing Love Pakistan"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'splash'

    def on_enter(self):
        """Auto-transition to home after splash duration"""
        from app.utils.constants import SPLASH_DURATION
        Clock.schedule_once(lambda dt: self._go_to_home(), SPLASH_DURATION)

    def _go_to_home(self):
        """Switch to home screen"""
        self.manager.current = 'home'
        self.manager.transition.direction = 'left'