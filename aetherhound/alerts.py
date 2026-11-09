"""Alerter: Audio and Visual Alert Notification Subsystem.
Flashes UI, triggers terminal bell, sounds hardware buzzer (Raspberry Pi GPIO or Windows beep),
and logs security alerts when an anomalous reconstruction error occurs.
"""
import sys, os, time

class Alerter:
    def __init__(self, cfg):
        self.muted = False
        self.bell = cfg.get("bell", True)
        self.buzzer_gpio = cfg.get("buzzer_gpio")
        self.buzzer = None
        self._last_alert_time = 0.0
        self.cooldown_sec = 0.5  # Prevent buzzing overload
        
        # 1. Raspberry Pi GPIO Buzzer
        if self.buzzer_gpio is not None:
            try:
                from gpiozero import Buzzer
                self.buzzer = Buzzer(self.buzzer_gpio)
            except Exception:
                try:
                    import RPi.GPIO as GPIO
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(self.buzzer_gpio, GPIO.OUT)
                    self.buzzer = "rpi_gpio"
                except Exception:
                    self.buzzer = None

    def fire(self, freq=1800, duration_ms=180):
        if self.muted:
            return
        now = time.time()
        if now - self._last_alert_time < self.cooldown_sec:
            return
        self._last_alert_time = now

        # Terminal visual & audible bell
        if self.bell:
            sys.stdout.write("\a")
            sys.stdout.flush()

        # Local hardware buzzer on Windows
        if sys.platform == "win32":
            try:
                import winsound
                # Non-blocking / short tone
                winsound.Beep(int(min(3000, max(400, freq))), int(duration_ms))
            except Exception:
                pass
                
        # Hardware buzzer on Raspberry Pi
        if self.buzzer:
            try:
                if hasattr(self.buzzer, "beep"):
                    self.buzzer.beep(on_time=0.15, off_time=0.1, n=2, background=True)
                elif self.buzzer == "rpi_gpio":
                    import RPi.GPIO as GPIO
                    GPIO.output(self.buzzer_gpio, GPIO.HIGH)
                    time.sleep(duration_ms / 1000.0)
                    GPIO.output(self.buzzer_gpio, GPIO.LOW)
            except Exception:
                pass
