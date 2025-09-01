from PyQt6 import QtWidgets, QtCore, QtGui
import keyboard
from copy import deepcopy

from modules import (
    APP_VERSION,
    DEFAULT_CONFIG_STRUCT,
    OVERLAY_POSITIONS, 
    TARGET_LANGUAGES,
    SOURCE_LANGUAGES,
    TRANSLATOR_ENGINES
)

class HotkeyDialog(QtWidgets.QDialog):
    def __init__(self, current_hotkey_str, hotkey_type="general", parent=None):
        super().__init__(parent)
        if hotkey_type == "translate":
            self.setWindowTitle("Change Hotkey (Translation)")
        elif hotkey_type == "copy":
            self.setWindowTitle("Change Hotkey (Copy)")
        else:
            self.setWindowTitle(f"Change Hotkey ({hotkey_type})")
        self.setModal(True)
        self.setMinimumWidth(350)

        self.initial_hotkey = current_hotkey_str
        self.new_hotkey_str = current_hotkey_str

        self.layout = QtWidgets.QVBoxLayout(self)
        self.info_label = QtWidgets.QLabel(
            "Press the 'Record' button, then press the desired key combination.\n"
            "The combination will be automatically captured.\n"
            "You can also enter the shortcut manually (e.g. ctrl+alt+p)."
        )
        self.info_label.setWordWrap(True)
        self.layout.addWidget(self.info_label)

        self.hotkey_input_display = QtWidgets.QLineEdit(current_hotkey_str)
        self.layout.addWidget(self.hotkey_input_display)

        self.record_button = QtWidgets.QPushButton("Record Hotkey")
        self.record_button.clicked.connect(self.toggle_recording_hotkey)
        self.layout.addWidget(self.record_button)

        self.recording_status_label = QtWidgets.QLabel("Press the key combination...")
        self.recording_status_label.setVisible(False)
        self.layout.addWidget(self.recording_status_label)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_dialog)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.is_recording_active = False
        self.keyboard_hook_id = None
        self.currently_pressed_keys = set()
        self.recorded_key_combination_list = []

    def toggle_recording_hotkey(self):
        if not self.is_recording_active:
            self.is_recording_active = True
            self.currently_pressed_keys.clear()
            self.recorded_key_combination_list = []
            self.hotkey_input_display.clear()
            self.hotkey_input_display.setPlaceholderText("Recording... Press keys.")
            self.hotkey_input_display.setEnabled(False)
            self.recording_status_label.setVisible(True)
            self.record_button.setText("Stop Recording")
            self.keyboard_hook_id = keyboard.hook(self._handle_key_event_for_dialog, suppress=True)
            print("[HotkeyDialog] Started recording hotkey.")
        else:
            self._stop_hotkey_recording_session()
            print("[HotkeyDialog] Stopped recording hotkey (prematurely).")

    def _handle_key_event_for_dialog(self, event):
        if not self.is_recording_active: 
            return
        key_name = event.name
        if key_name is None: 
            return

        if key_name in ('ctrl_l', 'ctrl_r'): 
            key_name = 'ctrl'
        elif key_name in ('shift_l', 'shift_r'): 
            key_name = 'shift'
        elif key_name in ('alt_l', 'alt_r', 'alt gr'): 
            key_name = 'alt'
        elif key_name in ('cmd_l', 'cmd_r', 'win_l', 'win_r', 'left windows', 'right windows', 'meta'): 
            key_name = 'win'

        known_modifiers = {'ctrl', 'shift', 'alt', 'win'}

        if event.event_type == keyboard.KEY_DOWN:
            if key_name not in self.currently_pressed_keys:
                self.currently_pressed_keys.add(key_name)

            if key_name not in known_modifiers:
                self.recorded_key_combination_list = sorted([k for k in self.currently_pressed_keys if k in known_modifiers])
                if key_name not in self.recorded_key_combination_list:
                    self.recorded_key_combination_list.append(key_name)
                self._update_hotkey_display_from_list()
                self._stop_hotkey_recording_session()
            else:
                temp_display_list = sorted([k for k in self.currently_pressed_keys if k in known_modifiers])
                current_display = " + ".join(temp_display_list)
                if temp_display_list:
                    current_display += " + ..."
                else:
                    current_display = "Press keys..."
                self.hotkey_input_display.setText(current_display)

        elif event.event_type == keyboard.KEY_UP:
            if key_name in self.currently_pressed_keys:
                self.currently_pressed_keys.remove(key_name)
            if self.is_recording_active:
                temp_display_list = sorted([k for k in self.currently_pressed_keys if k in known_modifiers])
                current_display = " + ".join(temp_display_list)
                if temp_display_list:
                    current_display += " + ..."
                else:
                    current_display = "Press keys..."
                self.hotkey_input_display.setText(current_display)

    def _update_hotkey_display_from_list(self):
        if self.recorded_key_combination_list:
            self.new_hotkey_str = "+".join(self.recorded_key_combination_list)
            self.hotkey_input_display.setText(self.new_hotkey_str)
        else:
            self.hotkey_input_display.setText(self.initial_hotkey)
            self.new_hotkey_str = self.initial_hotkey

    def _stop_hotkey_recording_session(self):
        if self.is_recording_active:
            self.is_recording_active = False
            if self.keyboard_hook_id:
                keyboard.unhook(self.keyboard_hook_id)
                self.keyboard_hook_id = None
            self.hotkey_input_display.setEnabled(True)
            self.recording_status_label.setVisible(False)
            self.record_button.setText("Record Hotkey")
            if not self.recorded_key_combination_list:
                self.hotkey_input_display.setText(self.initial_hotkey)
                self.new_hotkey_str = self.initial_hotkey

    def accept_dialog(self):
        if self.is_recording_active: 
            self._stop_hotkey_recording_session()
        final_text = self.hotkey_input_display.text().strip().lower()
        if not final_text or "..." in final_text or final_text == "press keys...":
            QtWidgets.QMessageBox.warning(self, "Incomplete Hotkey", "No valid shortcut was recorded or entered.")
            return
        try:
            keyboard.parse_hotkey(final_text)
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Hotkey Format",
                                          f"The shortcut '{final_text}' has an invalid format.\n"
                                          "Examples: 'ctrl+shift+a', 'alt+f1', 'win+space'.")
            return
        self.new_hotkey_str = final_text
        self.accept()

    def get_hotkey(self): 
        return self.new_hotkey_str

    def closeEvent(self, event):
        if self.is_recording_active: 
            self._stop_hotkey_recording_session()
        super().closeEvent(event)

class SettingsWindow(QtWidgets.QWidget):
    def __init__(self, tray_app, current_config_ref,
                 register_hotkey_translation_func, register_hotkey_copy_func,
                 save_config_func, app_version_ref):
        super().__init__()
        self.tray_app = tray_app
        self.current_config_ref = current_config_ref
        self.register_hotkey_translation_func = register_hotkey_translation_func
        self.register_hotkey_copy_func = register_hotkey_copy_func
        self.save_config_func = save_config_func
        self.app_version = app_version_ref
        self.overlay_positions_map = OVERLAY_POSITIONS
        self.target_languages_map = TARGET_LANGUAGES
        self.translator_engines_map = TRANSLATOR_ENGINES

        self.setWindowTitle("TranslatorOverlay Settings")
        self.resize(850, 650)
        self.setMinimumSize(850, 650)
        self.apply_theme()

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 14, 24, 14)
        main_layout.setSpacing(7)

        version_label = QtWidgets.QLabel(f"Version: {self.app_version}")
        lang_layout = QtWidgets.QHBoxLayout()
        source_lang_label = QtWidgets.QLabel("Source language (Google Speech Web API):")
        self.source_lang_combo = QtWidgets.QComboBox()
        for code, name in SOURCE_LANGUAGES.items():
            self.source_lang_combo.addItem(name, code)
        current_source_index = 0
        for i, (code, _) in enumerate(SOURCE_LANGUAGES.items()):
            if code == self.current_config_ref.get("source_language", "pl-PL"):
                current_source_index = i
        self.source_lang_combo.setCurrentIndex(current_source_index)
        self.source_lang_combo.currentIndexChanged.connect(self.change_source_language)

        target_lang_label = QtWidgets.QLabel("Target language (LibreTranslate):")
        self.target_lang_combo = QtWidgets.QComboBox()
        for code, name in TARGET_LANGUAGES.items():
            self.target_lang_combo.addItem(name, code)
        current_target_index = 0
        for i, (code, _) in enumerate(TARGET_LANGUAGES.items()):
            if code == self.current_config_ref.get("target_language", "en"):
                current_target_index = i
        self.target_lang_combo.setCurrentIndex(current_target_index)
        self.target_lang_combo.currentIndexChanged.connect(self.change_target_language)

        lang_layout.addWidget(source_lang_label)
        lang_layout.addWidget(self.source_lang_combo)
        lang_layout.addSpacing(20)
        lang_layout.addWidget(target_lang_label)
        lang_layout.addWidget(self.target_lang_combo)
        main_layout.addWidget(version_label)
        main_layout.addLayout(lang_layout)
        main_layout.addSpacing(6)

        hotkey_layout = QtWidgets.QHBoxLayout()
        self.hotkey_edit = QtWidgets.QLineEdit(self.current_config_ref.get("hotkey_translate", "ctrl+m"))
        self.hotkey_edit.setReadOnly(True)
        self.hotkey_edit.setMaximumWidth(120)
        hotkey_btn = QtWidgets.QPushButton("Change Translation Hotkey")
        hotkey_btn.setMinimumWidth(250)
        hotkey_btn.clicked.connect(self.change_translation_hotkey)
        hotkey_layout.addWidget(self.hotkey_edit)
        hotkey_layout.addWidget(hotkey_btn)
        main_layout.addLayout(hotkey_layout)

        copy_layout = QtWidgets.QHBoxLayout()
        self.copy_hotkey_edit = QtWidgets.QLineEdit(self.current_config_ref.get("hotkey_copy", "ctrl+shift+c"))
        self.copy_hotkey_edit.setReadOnly(True)
        self.copy_hotkey_edit.setMaximumWidth(120)
        copy_btn = QtWidgets.QPushButton("Change Copy Hotkey")
        copy_btn.setMinimumWidth(250)
        copy_btn.clicked.connect(self.change_copy_hotkey)
        copy_layout.addWidget(self.copy_hotkey_edit)
        copy_layout.addWidget(copy_btn)
        main_layout.addLayout(copy_layout)

        pos_label = QtWidgets.QLabel("Overlay position:")
        self.pos_combo = QtWidgets.QComboBox()
        for key, name in self.overlay_positions_map.items():
            self.pos_combo.addItem(name, key)
        current_index = 0
        for i, (key, _) in enumerate(self.overlay_positions_map.items()):
            if key == self.current_config_ref["overlay_position"]:
                current_index = i
        self.pos_combo.setCurrentIndex(current_index)
        self.pos_combo.currentIndexChanged.connect(self.change_overlay_position)
        main_layout.addWidget(pos_label)
        main_layout.addWidget(self.pos_combo)
        
        engine_layout = QtWidgets.QHBoxLayout()
        engine_label = QtWidgets.QLabel("Speech recognition engine:")
        self.engine_display = QtWidgets.QLabel("Google (Online)")
        self.engine_display.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                color: #808080;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        
        engine_layout.addWidget(engine_label)
        engine_layout.addWidget(self.engine_display)
        main_layout.addLayout(engine_layout)

        translator_layout = QtWidgets.QHBoxLayout()
        translator_label = QtWidgets.QLabel("Translation engine:")
        self.translator_display = QtWidgets.QLabel("LibreTranslate (Local)")
        self.translator_display.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                color: #808080;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        
        translator_layout.addWidget(translator_label)
        translator_layout.addWidget(self.translator_display)
        main_layout.addLayout(translator_layout)

        display_time_layout = QtWidgets.QHBoxLayout()
        display_time_label = QtWidgets.QLabel("Overlay display time (seconds):")
        self.display_time_spinbox = QtWidgets.QSpinBox()
        self.display_time_spinbox.setMinimum(5)
        self.display_time_spinbox.setMaximum(60)
        self.display_time_spinbox.setValue(self.current_config_ref.get("overlay_display_time", 15))
        self.display_time_spinbox.valueChanged.connect(self.change_display_time)
        
        display_time_layout.addWidget(display_time_label)
        display_time_layout.addWidget(self.display_time_spinbox)
        main_layout.addLayout(display_time_layout)
        
        phrase_time_layout = QtWidgets.QHBoxLayout()
        phrase_time_label = QtWidgets.QLabel("Maximum recording time (seconds):")
        self.phrase_time_spinbox = QtWidgets.QSpinBox()
        self.phrase_time_spinbox.setMinimum(10)
        self.phrase_time_spinbox.setMaximum(120)
        self.phrase_time_spinbox.setValue(self.current_config_ref.get("phrase_time_limit", 30))
        self.phrase_time_spinbox.valueChanged.connect(self.change_phrase_time_limit)
        
        phrase_time_layout.addWidget(phrase_time_label)
        phrase_time_layout.addWidget(self.phrase_time_spinbox)
        main_layout.addLayout(phrase_time_layout)

        initial_silence_layout = QtWidgets.QHBoxLayout()
        initial_silence_label = QtWidgets.QLabel("Initial silence timeout (start detection):")
        initial_silence_layout.addWidget(initial_silence_label)
        initial_silence_layout.addSpacing(10)
        self.initial_silence_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.initial_silence_slider.setMinimum(15)
        self.initial_silence_slider.setMaximum(80)
        self.initial_silence_slider.setSingleStep(1)
        self.initial_silence_slider.setTickInterval(5)
        self.initial_silence_slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        initial_val = int(round(self.current_config_ref.get("initial_silence_timeout", 1.5) * 10))
        self.initial_silence_slider.setValue(initial_val)
        initial_silence_layout.addWidget(QtWidgets.QLabel("Shorter wait"))
        initial_silence_layout.addWidget(self.initial_silence_slider)
        initial_silence_layout.addWidget(QtWidgets.QLabel("Longer wait"))
        self.initial_silence_value_label = QtWidgets.QLabel(f"{self.initial_silence_slider.value()/10:.1f} s")
        initial_silence_layout.addWidget(self.initial_silence_value_label)
        main_layout.addLayout(initial_silence_layout)
        self.initial_silence_slider.valueChanged.connect(self.change_initial_silence_slider)

        libre_url_layout = QtWidgets.QHBoxLayout()
        libre_url_label = QtWidgets.QLabel("LibreTranslate local server URL:")
        self.libre_url_edit = QtWidgets.QLineEdit()
        self.libre_url_edit.setText(self.current_config_ref.get("libretranslate_url", "http://localhost:5000/translate"))
        self.libre_url_edit.setMinimumWidth(350)
        self.libre_url_edit.setPlaceholderText("e.g. http://localhost:5000/translate")
        libre_url_layout.addWidget(libre_url_label)
        libre_url_layout.addWidget(self.libre_url_edit)
        main_layout.addLayout(libre_url_layout)
        self.libre_url_edit.textChanged.connect(self.auto_save_libre_url)
        
        main_layout.addStretch()
        
        button_layout = QtWidgets.QHBoxLayout()
        
        reset_btn = QtWidgets.QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        exit_btn = QtWidgets.QPushButton("Kill process")
        exit_btn.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; font-weight: bold; }")
        exit_btn.clicked.connect(self.exit_application)
        button_layout.addWidget(exit_btn)
        
        main_layout.addLayout(button_layout)

    def apply_theme(self, dark_mode=False):
        stylesheet = """
            QWidget {
                background-color: #f6f6f6; 
                color: #232629;
            }
            QTabWidget::pane { 
                border: 1px solid #bbb; 
            }
            QTabBar::tab { 
                background: #eaeaea; 
                color: #232629; 
                border: 1px solid #bbb; 
                padding: 8px; 
                border-radius: 8px; 
            }
            QTabBar::tab:selected { 
                background: #ffffff; 
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox {
                background-color: #ffffff; 
                color: #232629; 
                border: 1px solid #bbb; 
                border-radius: 6px; 
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView {
                border-radius: 4px;
                background: #ffffff;
                color: #232629;
                selection-background-color: #eaeaea;
                selection-color: #232629;
                border: 1px solid #bbb;
                padding: 2px 0px;
                outline: none;
            }
            QComboBox {
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton { 
                background-color: #eaeaea; 
                color: #232629; 
                border: 1px solid #bbb; 
                border-radius: 6px; 
                padding: 6px 12px; 
            }
            QPushButton:hover { 
                background-color: #d6d6d6; 
            }
            QLabel { 
                color: #232629; 
            }
        """
        self.setStyleSheet(stylesheet)

    def change_translation_hotkey(self):
        dialog = HotkeyDialog(self.current_config_ref.get("hotkey_translate", "ctrl+m"), hotkey_type="translate", parent=self)
        if dialog.exec():
            new_hotkey = dialog.get_hotkey()
            if new_hotkey and new_hotkey != self.current_config_ref.get("hotkey_translate", "ctrl+m"):
                current_copy_hotkey = self.current_config_ref.get("hotkey_copy", "ctrl+shift+c")
                if new_hotkey == current_copy_hotkey:
                    QtWidgets.QMessageBox.warning(
                        self, 
                        "Duplicate Hotkey", 
                        f"The hotkey '{new_hotkey}' is already used by the copy function.\n"
                        "Each function must have a unique keyboard shortcut."
                    )
                    dialog.deleteLater()
                    return
                
                if self.register_hotkey_translation_func(new_hotkey):
                    self.hotkey_edit.setText(new_hotkey)
        dialog.deleteLater()

    def change_copy_hotkey(self):
        dialog = HotkeyDialog(self.current_config_ref.get("hotkey_copy", "ctrl+shift+c"), hotkey_type="copy", parent=self)
        if dialog.exec():
            new_hotkey = dialog.get_hotkey()
            if new_hotkey and new_hotkey != self.current_config_ref.get("hotkey_copy", "ctrl+shift+c"):
                current_translate_hotkey = self.current_config_ref.get("hotkey_translate", "ctrl+m")
                if new_hotkey == current_translate_hotkey:
                    QtWidgets.QMessageBox.warning(
                        self, 
                        "Duplicate Hotkey", 
                        f"The hotkey '{new_hotkey}' is already used by the translation function.\n"
                        "Each function must have a unique keyboard shortcut."
                    )
                    dialog.deleteLater()
                    return
                if self.register_hotkey_copy_func(new_hotkey):
                    self.copy_hotkey_edit.setText(new_hotkey)
        dialog.deleteLater()

    def change_overlay_position(self):
        key = self.pos_combo.currentData()
        if key != self.current_config_ref["overlay_position"]:
            self.tray_app.change_position(key)

    def change_display_time(self, value):
        self.current_config_ref["overlay_display_time"] = value
        self.save_config_func()

    def change_phrase_time_limit(self, value):
        self.current_config_ref["phrase_time_limit"] = value
        self.save_config_func()

    def change_target_language(self):
        code = self.target_lang_combo.currentData()
        self.current_config_ref["target_language"] = code
        self.save_config_func()

    def change_source_language(self):
        code = self.source_lang_combo.currentData()
        self.current_config_ref["source_language"] = code
        self.save_config_func()

    def auto_save_libre_url(self):
        url = self.libre_url_edit.text().strip()
        if url.startswith("http://") or url.startswith("https://"):
            self.current_config_ref["libretranslate_url"] = url
            self.save_config_func()

    def reset_to_defaults(self):
        defaults = deepcopy(DEFAULT_CONFIG_STRUCT)

        prev_config = deepcopy(self.current_config_ref)
        changed_keys = []
        for k, v in defaults.items():
            if prev_config.get(k) != v:
                changed_keys.append(k)

        suppress_prev = getattr(self.tray_app, '_suppress_tray_messages', False)
        try:
            setattr(self.tray_app, '_suppress_tray_messages', True)

            try:
                self.current_config_ref.clear()
                self.current_config_ref.update(defaults)
            except Exception:
                self.current_config_ref = defaults

            try:
                self.hotkey_edit.setText(self.current_config_ref.get("hotkey_translate", DEFAULT_CONFIG_STRUCT["hotkey_translate"]))
                self.copy_hotkey_edit.setText(self.current_config_ref.get("hotkey_copy", DEFAULT_CONFIG_STRUCT["hotkey_copy"]))

                desired_pos = self.current_config_ref.get("overlay_position", DEFAULT_CONFIG_STRUCT["overlay_position"]) 
                for i in range(self.pos_combo.count()):
                    if self.pos_combo.itemData(i) == desired_pos:
                        self.pos_combo.setCurrentIndex(i)
                        break

                self.display_time_spinbox.setValue(int(self.current_config_ref.get("overlay_display_time", DEFAULT_CONFIG_STRUCT["overlay_display_time"])))
                self.phrase_time_spinbox.setValue(int(self.current_config_ref.get("phrase_time_limit", DEFAULT_CONFIG_STRUCT["phrase_time_limit"])))
                init_val = int(round(self.current_config_ref.get("initial_silence_timeout", DEFAULT_CONFIG_STRUCT.get("initial_silence_timeout", 4.0)) * 10))
                self.initial_silence_slider.setValue(init_val)
                try:
                    self.initial_silence_value_label.setText(f"{self.initial_silence_slider.value()/10:.1f} s")
                except Exception:
                    pass

                try:
                    self.libre_url_edit.setText(self.current_config_ref.get("libretranslate_url", DEFAULT_CONFIG_STRUCT.get("libretranslate_url", "http://localhost:5000/translate")))
                except Exception:
                    pass

                src = self.current_config_ref.get("source_language")
                for i in range(self.source_lang_combo.count()):
                    if self.source_lang_combo.itemData(i) == src:
                        self.source_lang_combo.setCurrentIndex(i)
                        break
                tgt = self.current_config_ref.get("target_language")
                for i in range(self.target_lang_combo.count()):
                    if self.target_lang_combo.itemData(i) == tgt:
                        self.target_lang_combo.setCurrentIndex(i)
                        break
            except Exception:
                pass

            try:
                self.register_hotkey_translation_func(self.current_config_ref.get("hotkey_translate"))
            except Exception:
                pass
            try:
                self.register_hotkey_copy_func(self.current_config_ref.get("hotkey_copy"))
            except Exception:
                pass

            try:
                if hasattr(self.tray_app, 'overlay_window') and self.tray_app.overlay_window:
                    self.tray_app.overlay_window.update_settings_from_config(self.current_config_ref)
                    if hasattr(self.tray_app, 'change_position'):
                        self.tray_app.change_position(self.current_config_ref.get("overlay_position"))
            except Exception:
                pass

            try:
                self.save_config_func()
            except Exception:
                pass
        finally:
            setattr(self.tray_app, '_suppress_tray_messages', suppress_prev)

        if changed_keys:
            friendly_names = {
                'hotkey_translate': 'Translation hotkey',
                'hotkey_copy': 'Copy hotkey',
                'overlay_position': 'Overlay position',
                'target_language': 'Target language',
                'source_language': 'Source language',
                'overlay_display_time': 'Overlay display time',
                'phrase_time_limit': 'Max recording time',
                'libretranslate_url': 'LibreTranslate URL',
            }
            items = [friendly_names.get(k, k) for k in changed_keys]
            if len(items) > 6:
                items = items[:6] + ['…']
            summary = 'Defaults applied: ' + ', '.join(items)
        else:
            summary = 'Defaults applied (no changes needed).'

        try:
            if hasattr(self.tray_app, 'tray_icon') and self.tray_app.tray_icon:
                self.tray_app.tray_icon.showMessage('OverlayTranslator', summary, QtWidgets.QSystemTrayIcon.MessageIcon.Information, 3500)
        except Exception:
            try:
                QtWidgets.QMessageBox.information(self, 'Defaults applied', summary)
            except Exception:
                pass



    def exit_application(self):
        """Completely closes the application after user confirmation"""
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Close Confirmation")
        msg_box.setText("Kill process will completely close the application. Are you sure you want to do this?")
        yes_btn = msg_box.addButton("Yes", QtWidgets.QMessageBox.ButtonRole.YesRole)
        no_btn = msg_box.addButton("No", QtWidgets.QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_btn)
        msg_box.exec()

        if msg_box.clickedButton() == yes_btn:
            print("[GUI] User confirmed to close the application via GUI")
            self.close()
            self.tray_app.quit_app()

    def change_initial_silence_slider(self, value):
        float_val = value / 10.0
        self.initial_silence_value_label.setText(f"{float_val:.1f} s")
        self.current_config_ref["initial_silence_timeout"] = float_val
        self.save_config_func()
