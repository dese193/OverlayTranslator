import sys
import os
import json
import threading
import speech_recognition as sr
import keyboard
from PyQt6 import QtWidgets, QtCore, QtGui
from pathlib import Path
from copy import deepcopy
import time
import requests


from constants import (
    APP_NAME, APP_VERSION,
    DEFAULT_CONFIG_STRUCT,
    OVERLAY_POSITIONS, TARGET_LANGUAGES, TRANSLATOR_ENGINES,
    DEFAULT_HOTKEY, DEFAULT_COPY_HOTKEY, DEFAULT_OVERLAY_POSITION,
    DEFAULT_RECOGNIZER_ENGINE, DEFAULT_TRANSLATOR_ENGINE,
    DEFAULT_PHRASE_TIME_LIMIT,
    DEFAULT_SOURCE_LANGUAGE, DEFAULT_LIBRETRANSLATE_URL,
    DEFAULT_INITIAL_SILENCE_TIMEOUT,
    DEFAULT_SILENCE_TIMEOUT,
)

try:
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("WARNING: pywin32 modules are not installed. The 'click-through' feature will not work.")
    print("To install: pip install pywin32")


from gui import SettingsWindow, HotkeyDialog
from overlay import OverlayWindow

current_config = deepcopy(DEFAULT_CONFIG_STRUCT)
active_hotkey = current_config["hotkey_translate"]
active_copy_hotkey = current_config["hotkey_copy"]

last_translated_text = ""

active_hotkey_listener = None
active_copy_hotkey_listener = None


def get_config_dir():
    if sys.platform == "win32":
        path = Path(os.getenv('APPDATA', '')) / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        path = Path.home() / ".config" / APP_NAME
    
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"WARNING: Cannot create config folder {path}: {e}")
        path = Path(".") / APP_NAME
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e_fallback:
            print(f"CRITICAL ERROR: Cannot create config folder: {e_fallback}")
            return None
    return path

CONFIG_DIR = get_config_dir()
CONFIG_FILE_PATH = CONFIG_DIR / "settings.json" if CONFIG_DIR else None

def load_config():
    global current_config, active_hotkey, active_copy_hotkey
    if CONFIG_FILE_PATH and CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                loaded_values = json.load(f)
                valid_config = deepcopy(DEFAULT_CONFIG_STRUCT)
                for key in valid_config:
                    if key in loaded_values:
                        valid_config[key] = loaded_values[key]
                if "initial_silence_timeout" not in valid_config or not isinstance(valid_config["initial_silence_timeout"], (float, int)):
                    valid_config["initial_silence_timeout"] = DEFAULT_INITIAL_SILENCE_TIMEOUT
                else:
                    valid_config["initial_silence_timeout"] = float(valid_config["initial_silence_timeout"])
                # silence_timeout
                valid_config["silence_timeout"] = 0.20
                current_config = valid_config
                if current_config.get("overlay_position") not in OVERLAY_POSITIONS:
                    current_config["overlay_position"] = DEFAULT_OVERLAY_POSITION
        except json.JSONDecodeError:
            print(f"[Config] Error: Config file {CONFIG_FILE_PATH} is corrupted. Using default settings.")
        except Exception as e:
            print(f"[Config] Unexpected error while loading config: {e}. Using default settings.")
    else:
        print("[Config] Using default settings (config file does not exist or an error occurred).")
        current_config = deepcopy(DEFAULT_CONFIG_STRUCT)
    if "initial_silence_timeout" not in current_config or not isinstance(current_config["initial_silence_timeout"], (float, int)):
        current_config["initial_silence_timeout"] = DEFAULT_INITIAL_SILENCE_TIMEOUT
    else:
        current_config["initial_silence_timeout"] = float(current_config["initial_silence_timeout"])
    # silence_timeout
    current_config["silence_timeout"] = 0.20
    active_hotkey = current_config["hotkey_translate"]
    active_copy_hotkey = current_config["hotkey_copy"]

def save_config():
    global current_config
    if "initial_silence_timeout" not in current_config or not isinstance(current_config["initial_silence_timeout"], (float, int)):
        current_config["initial_silence_timeout"] = DEFAULT_INITIAL_SILENCE_TIMEOUT
    else:
        current_config["initial_silence_timeout"] = float(current_config["initial_silence_timeout"])
    # silence_timeout
    current_config["silence_timeout"] = 0.20
    if CONFIG_FILE_PATH:
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Config] Error while saving config: {e}")
    else:
        print("[Config] WARNING: Cannot save configuration, file path is not available.")


class SystemTrayApp:
    def __init__(self, app_instance, overlay_window_instance):
        self.app = app_instance
        self.overlay_window = overlay_window_instance
        self.tray_icon = QtWidgets.QSystemTrayIcon(self.app)
        self.debug_console_window = None

        # tray
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.abspath(".")
        else:
            base_path = os.path.dirname(__file__)
        icon_path = os.path.join(base_path, "pythonicon.ico")
        if os.path.exists(icon_path):
            icon = QtGui.QIcon(icon_path)
            print(f"[Icon] Loaded custom icon from: {icon_path}")
        else:
            print(f"[Icon] WARNING: Icon file '{icon_path}' not found. Using default system icon.")
            icon = self.app.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        self.menu = QtWidgets.QMenu()

        # settings panel
        settings_action = QtGui.QAction("Open Settings", self.app)
        settings_action.triggered.connect(self.show_settings_window)
        self.menu.addAction(settings_action)
        self.menu.addSeparator()

        exit_action = QtGui.QAction("Exit", self.app)
        exit_action.triggered.connect(self.quit_app)
        self.menu.addAction(exit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        self.settings_window = None

    def change_position(self, position_key):
        global current_config
        old_position = current_config["overlay_position"]
        if old_position != position_key:
            self.overlay_window.reposition_overlay(position_key, is_test_display=True)
            current_config["overlay_position"] = position_key
            save_config()
            self.tray_icon.showMessage("OverlayTranslator", f"Position changed to: {OVERLAY_POSITIONS.get(position_key, 'Unknown')}", self.tray_icon.icon(), 2000)
        else:
            pass

    def show_settings_window(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self, current_config,
                                                  self.register_hotkey_translation_internal,
                                                  self.register_hotkey_copy_internal,
                                                  save_config,
                                                  APP_VERSION,
                                                  )
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def register_hotkey_translation_internal(self, new_hotkey_str):
        global active_hotkey
        try:
            register_hotkey_translation(new_hotkey_str, self.overlay_window)
            current_config["hotkey_translate"] = new_hotkey_str
            active_hotkey = new_hotkey_str
            save_config()
            self.tray_icon.showMessage("OverlayTranslator", f"Translation hotkey changed to: {new_hotkey_str.upper()}", self.tray_icon.icon(), 2000)
            return True
        except (ValueError, KeyError) as e:
            print(f"[Hotkey] Error while changing translation hotkey: {e}")
            QtWidgets.QMessageBox.warning(self.overlay_window, "Hotkey Change Error",
                f"Failed to set shortcut '{new_hotkey_str.upper()}'.\nError: {e}\n\n"
                f"Previous shortcut '{active_hotkey.upper()}' remains active.")
            try: register_hotkey_translation(active_hotkey, self.overlay_window)
            except Exception as e_restore:
                print(f"[Hotkey] CRITICAL ERROR while trying to restore old translation hotkey: {e_restore}")
                QtWidgets.QMessageBox.critical(self.overlay_window, "Critical Error", f"Failed to restore previous hotkey! {e_restore}")
            return False

    def register_hotkey_copy_internal(self, new_hotkey_str):
        global active_copy_hotkey
        try:
            register_hotkey_copy(new_hotkey_str, self.overlay_window)
            current_config["hotkey_copy"] = new_hotkey_str
            active_copy_hotkey = new_hotkey_str
            save_config()
            self.tray_icon.showMessage("OverlayTranslator", f"Copy hotkey changed to: {new_hotkey_str.upper()}", self.tray_icon.icon(), 2000)
            return True
        except (ValueError, KeyError) as e:
            print(f"[Hotkey] Error while changing copy hotkey: {e}")
            QtWidgets.QMessageBox.warning(self.overlay_window, "Hotkey Change Error",
                f"Failed to set shortcut '{new_hotkey_str.upper()}'.\nError: {e}\n\n"
                f"Previous shortcut '{active_copy_hotkey.upper()}' remains active.")
            try:
                register_hotkey_copy(active_copy_hotkey, self.overlay_window)
            except Exception as e_restore:
                print(f"[Hotkey] CRITICAL ERROR while trying to restore old copy hotkey: {e_restore}")
                QtWidgets.QMessageBox.critical(self.overlay_window, "Critical Error", f"Failed to restore previous hotkey! {e_restore}")
            return False

    def quit_app(self):
        print("[App] Closing application...")
        save_config()
        keyboard.unhook_all()
        if hasattr(self, 'debug_console_window') and self.debug_console_window:
            self.debug_console_window.close()
        self.tray_icon.hide()
        QtCore.QCoreApplication.quit()

recognizer = sr.Recognizer()

transcription_thread = None
is_listening = False
listen_stop_event = threading.Event()
speech_prompt_timer = None

def show_speak_now_prompt(overlay_window, engine_name):
    """Wyświetl 'Speak now...' tylko jeśli trwa aktywne nasłuchiwanie."""
    if is_listening and not listen_stop_event.is_set():
        overlay_window.show_text_signal.emit(f"Speak now ({engine_name})...", False, False)

def refresh_speech_prompt(overlay_window, engine_name):
    global speech_prompt_timer
    if is_listening and not listen_stop_event.is_set() and speech_prompt_timer is not None:
        show_speak_now_prompt(overlay_window, engine_name)
        speech_prompt_timer = threading.Timer(4.5, refresh_speech_prompt, [overlay_window, engine_name])
        speech_prompt_timer.daemon = True
        speech_prompt_timer.start()

def translate_text_libretranslate_local(text, source_lang="pl", target_lang="en", server_url="http://localhost:5000/translate"):
    """
    Translate text using local LibreTranslate Docker server (no API key required)
    """
    try:
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(server_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("translatedText", "")
        else:
            print(f"LibreTranslate API Error: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"LibreTranslate Request Error: {e}")
        return None
    except Exception as e:
        print(f"LibreTranslate Unexpected Error: {e}")
        return None

def transcribe_and_translate(overlay_window):
    global is_listening, last_translated_text, current_config, speech_prompt_timer
    overlay_window.update_settings_from_config(current_config)
    is_listening = True
    overlay_window.hide_overlay_and_clear_text()
    listen_stop_event.clear()
    final_transcription = ""
    try:
        overlay_window.show_text_signal.emit("Calibrating noise (Google)...", False, False)
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                overlay_window.show_text_signal.emit("Speak now (Google)...", False, False)
                if speech_prompt_timer is not None:
                    speech_prompt_timer.cancel()
                speech_prompt_timer = threading.Timer(4.5, refresh_speech_prompt, [overlay_window, "Google"])
                speech_prompt_timer.daemon = True
                speech_prompt_timer.start()
                max_total_time = current_config.get("phrase_time_limit", 30)
                initial_silence = current_config.get("initial_silence_timeout", DEFAULT_INITIAL_SILENCE_TIMEOUT)
                segment_silence = 0.20
                start_time = time.time()
                audio_segments = []
                try:
                    audio = recognizer.listen(
                        source,
                        timeout=initial_silence,
                        phrase_time_limit=min(5, max_total_time)
                    )
                    audio_segments.append(audio)
                except sr.WaitTimeoutError:
                    overlay_window.show_text_signal.emit("No speech detected.", False, True)
                    is_listening = False
                    listen_stop_event.set()
                    if speech_prompt_timer is not None:
                        speech_prompt_timer.cancel()
                        speech_prompt_timer = None
                    return
                while True:
                    if time.time() - start_time > max_total_time:
                        break
                    try:
                        audio = recognizer.listen(
                            source,
                            timeout=segment_silence,
                            phrase_time_limit=min(5, max_total_time - (time.time() - start_time))
                        )
                        audio_segments.append(audio)
                    except sr.WaitTimeoutError:
                        break
                if speech_prompt_timer is not None:
                    speech_prompt_timer.cancel()
                    speech_prompt_timer = None
                if not audio_segments:
                    overlay_window.show_text_signal.emit("No speech detected.", False, True)
                    is_listening = False
                    listen_stop_event.set()
                    return
                if len(audio_segments) == 1:
                    combined_audio = audio_segments[0]
                else:
                    raw_data = b''.join([a.get_raw_data() for a in audio_segments])
                    sample_rate = audio_segments[0].sample_rate
                    sample_width = audio_segments[0].sample_width
                    combined_audio = sr.AudioData(raw_data, sample_rate, sample_width)
                overlay_window.show_text_signal.emit("Processing speech (Google)...", False, False)
                final_transcription = recognizer.recognize_google(
                    combined_audio, 
                    language=current_config.get("source_language", DEFAULT_SOURCE_LANGUAGE)
                )
        except sr.UnknownValueError:
            overlay_window.show_text_signal.emit("Failed to recognize speech.", False, True)
            if speech_prompt_timer is not None:
                speech_prompt_timer.cancel()
                speech_prompt_timer = None
        except sr.RequestError as e:
            overlay_window.show_text_signal.emit(f"Google API Error: {e}", False, True)
            is_listening = False
            listen_stop_event.set()
            if speech_prompt_timer is not None:
                speech_prompt_timer.cancel()
                speech_prompt_timer = None
            return
        except Exception as e:
            overlay_window.show_text_signal.emit(f"Unexpected error in Google SR: {e}", False, True)
            is_listening = False
            listen_stop_event.set()
            if speech_prompt_timer is not None:
                speech_prompt_timer.cancel()
                speech_prompt_timer = None
            return
        if final_transcription:
            if speech_prompt_timer is not None:
                speech_prompt_timer.cancel()
                speech_prompt_timer = None
            overlay_window.show_text_signal.emit(f"Recognized: {final_transcription}", False, False)
            try:
                overlay_window.show_text_signal.emit("Translating (LibreTranslate)...", False, False)
                libretranslate_url = current_config.get("libretranslate_url", DEFAULT_LIBRETRANSLATE_URL)
                target_lang = current_config.get("target_language", "en")
                source_lang = current_config.get("source_language", DEFAULT_SOURCE_LANGUAGE)
                if source_lang.startswith("pl"):
                    source_lang = "pl"
                elif source_lang.startswith("en"):
                    source_lang = "en"
                translated_text = translate_text_libretranslate_local(
                    final_transcription, 
                    source_lang=source_lang,
                    target_lang=target_lang,
                    server_url=libretranslate_url
                )
                if translated_text is None:
                    overlay_window.show_text_signal.emit("LibreTranslate server error. Check if Docker server is running on localhost:5000", False, True)
                    return
                last_translated_text = translated_text
                overlay_window.show_text_signal.emit(translated_text, False, False)
            except Exception as e:
                overlay_window.show_text_signal.emit(f"Translation error: {e}", False, True)
    finally:
        is_listening = False
        listen_stop_event.set()
        if speech_prompt_timer is not None:
            speech_prompt_timer.cancel()
            speech_prompt_timer = None

def hotkey_callback_translation(overlay_window):
    global transcription_thread, is_listening
    if not is_listening:
        if transcription_thread and transcription_thread.is_alive():
            return
        transcription_thread = threading.Thread(target=transcribe_and_translate, args=(overlay_window,))
        transcription_thread.daemon = True
        transcription_thread.start()
    else:
        pass

def hotkey_callback_copy(overlay_window):
    global last_translated_text
    if last_translated_text:
        overlay_window.copy_to_clipboard_signal.emit(last_translated_text)
        overlay_window.show_text_signal.emit("Copied to clipboard!", False, True)
    else:
        overlay_window.show_text_signal.emit("No text to copy.", False, True)

def register_hotkey_translation(hotkey_str, overlay_window):
    global active_hotkey, active_hotkey_listener
    if active_hotkey_listener:
        try:
            keyboard.remove_hotkey(active_hotkey_listener)
        except KeyError:
            pass
        active_hotkey_listener = None
    try:
        active_hotkey_listener = keyboard.add_hotkey(hotkey_str, lambda: hotkey_callback_translation(overlay_window))
        active_hotkey = hotkey_str
        print(f"[Hotkey] Registered translation hotkey: {active_hotkey}")
    except (ValueError, KeyError) as e:
        print(f"[Hotkey] Error while registering translation hotkey '{hotkey_str}': {e}")
        raise

def register_hotkey_copy(hotkey_str, overlay_window):
    global active_copy_hotkey, active_copy_hotkey_listener
    if active_copy_hotkey_listener:
        try:
            keyboard.remove_hotkey(active_copy_hotkey_listener)
        except KeyError:
            pass
        active_copy_hotkey_listener = None
    try:
        active_copy_hotkey_listener = keyboard.add_hotkey(hotkey_str, lambda: hotkey_callback_copy(overlay_window))
        active_copy_hotkey = hotkey_str
        print(f"[Hotkey] Registered copy hotkey: {active_copy_hotkey}")
    except (ValueError, KeyError) as e:
        print(f"[Hotkey] Error while registering copy hotkey '{hotkey_str}': {e}")
        raise

def main():
    load_config()
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    icon_path = os.path.join(os.path.dirname(__file__), "pythonicon.ico")
    app.setWindowIcon(QtGui.QIcon(icon_path))
    overlay_window = OverlayWindow(
        initial_width=current_config["overlay_min_width"],
        initial_height=current_config["overlay_short_text_min_height"],
        initial_position_key=current_config["overlay_position"],
        font_size=current_config["font_size"],
        text_color=current_config["text_color"],
        background_color=current_config["background_color"],
        padding=current_config["padding"],
        overlay_min_width=current_config["overlay_min_width"],
        overlay_max_width=current_config["overlay_max_width"],
        overlay_min_height=current_config["overlay_min_height"],
        overlay_max_height=current_config["overlay_max_height"],
        overlay_short_text_min_height=current_config["overlay_short_text_min_height"],
        overlay_short_text_max_height=current_config["overlay_short_text_max_height"],
        overlay_display_time=current_config["overlay_display_time"],
        overlay_positions_map=OVERLAY_POSITIONS
    )
    overlay_window.setWindowIcon(QtGui.QIcon(icon_path))
    try:
        register_hotkey_translation(active_hotkey, overlay_window)
    except Exception as e:
        print(f"CRITICAL ERROR: Cannot register initial translation hotkey '{active_hotkey}'. The application may not work correctly. {e}")
        QtWidgets.QMessageBox.critical(None, "Hotkey Error",
                                       f"Failed to register initial translation hotkey: '{active_hotkey}'.\n"
                                       "Ensure the shortcut is not already in use by another program.\n"
                                       "The application will start, but the hotkey may not work.")
    try:
        register_hotkey_copy(active_copy_hotkey, overlay_window)
    except Exception as e:
        print(f"CRITICAL ERROR: Cannot register initial copy hotkey '{active_copy_hotkey}'. The application may not work correctly. {e}")
        QtWidgets.QMessageBox.critical(None, "Hotkey Error",
                                       f"Failed to register initial copy hotkey: '{active_copy_hotkey}'.\n"
                                       "Ensure the shortcut is not already in use by another program.\n"
                                       "The application will start, but the copy hotkey may not work.")
    tray_app = SystemTrayApp(app, overlay_window)
    tray_app.show_settings_window() 
    sys.exit(app.exec())

if __name__ == "__main__":
    main()