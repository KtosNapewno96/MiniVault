import ctypes
from ctypes import wintypes
import platform
from platform import system
import re
import sys
import psutil
from tkinter import filedialog, messagebox
from password_generator import PasswordGeneratorWindow
import config_manager as cfg
from learn_more import LearnMoreWindow
import multiprocessing
import tkinter as tk

import winreg


def get_cpu_name():
    """Pobiera pełną nazwę procesora z rejestru Windows."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )
        name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        return name.strip()
    except:
        return platform.processor()


def check_hardware_requirements():
    # --- 1. RAM CHECK ---
    # Convert total RAM to GB
    total_ram = psutil.virtual_memory().total / (1024**3)

    # Threshold 7.5 GB (Safe for 8GB systems with integrated graphics)
    if total_ram < 7.5:
        messagebox.showerror(
            "Hardware Requirement Error",
            f"Insufficient RAM.\n"
            f"Required: min. 8 GB RAM\n"
            f"Detected: {total_ram:.2f} GB",
        )
        return False

    # --- 2. CPU CHECK ---
    full_cpu_name = get_cpu_name()
    cpu_upper = full_cpu_name.upper()

    # VIP Series (Always allowed)
    vip_series = ["I7-", "I9-", "ULTRA", "XEON"]
    if any(vip in cpu_upper for vip in vip_series):
        print(f"Hardware OK: High-performance series detected ({full_cpu_name})")
        return True

    # i5 Series filter (min. 6th generation)
    if "I5-" in cpu_upper:
        match = re.search(r"I5-(\d{4,5})", cpu_upper)
        if match:
            model_number = int(match.group(1))
            # Block i5 models older than 6200
            if model_number < 6200:
                messagebox.showerror(
                    "Hardware Requirement Error",
                    f"Your i5 processor is too old for this application.\n"
                    f"Required: min. i5-6200U\n"
                    f"Detected: {full_cpu_name}",
                )
                return False
            return True
        return True

    # Block other series (i3, Celeron, Pentium, etc.)
    messagebox.showerror(
        "Hardware Requirement Error",
        f"Your processor does not meet the minimum requirements.\n"
        f"Required: Intel i5 (6th Gen+), i7, i9, Ultra or Xeon.\n"
        f"Detected: {full_cpu_name}",
    )
    return False


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


# WinAPI
kernel32.SetProcessWorkingSetSize.argtypes = [
    wintypes.HANDLE,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
kernel32.SetProcessWorkingSetSize.restype = wintypes.BOOL


def lock_process_memory():
    if platform.system() == "Windows":
        current_process_handle = wintypes.HANDLE(-1)

        min_size = 1 * 1024 * 1024
        max_size = 4 * 1024 * 1024 * 1024

        if not kernel32.SetProcessWorkingSetSize(
            current_process_handle, min_size, max_size
        ):
            err = kernel32.GetLastError()
            print(f"Błąd WinAPI: {err}")
            return False

        print("Sukces: Pamięć zoptymalizowana.")
        return True
    return False


import os
import winreg
import json
import zlib
import threading
import gc
from pathlib import Path

import customtkinter as ctk
from argon2.low_level import hash_secret_raw, Type
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

# ---------------- CONFIG ----------------
APP_NAME = "MiniVault 3.2"
local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
BASE_DIR = Path(local_appdata) / "Programs" / APP_NAME
VAULT_FILE = "vault.mvault"
MAGIC = b"AES-256"


# ---------------- MEMORY SECURITY ----------------
def scrub_sensitive(obj):
    if isinstance(obj, bytearray):
        for i in range(len(obj)):
            obj[i] = 0

    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = 0

    gc.collect(0)
    gc.collect(1)
    gc.collect(2)

    try:
        del obj
    except:
        pass


# ---------------- CRYPTOGRAPHY ----------------
HAS_SCRUBBER = False
scrub_lib = None
DLL_PATH = Path(__file__).parent / "_scrub_2.dll"

try:
    if DLL_PATH.exists():
        scrub_lib = ctypes.CDLL(str(DLL_PATH))
        scrub_lib.secure_scrub_argon2.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        scrub_lib.secure_scrub_argon2.restype = None
        HAS_SCRUBBER = True
        print(f"✅ Załadowano ASM: {DLL_PATH.name}")
    else:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "CRITICAL ERROR", f"ACCESS DENIED: Module '{DLL_PATH.name}' not found!"
        )
        sys.exit(1) 
except Exception as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "CRITICAL ERROR",
        f"ACCESS DENIED: Failed to initialize security module!\n\nError: {e}",
    )
    sys.exit(1)


def launch_learn_more():
    import customtkinter as ctk
    from learn_more import LearnMoreWindow

    root = ctk.CTk()
    root.withdraw()
    window = LearnMoreWindow(root)

    root.mainloop()


class CryptoManager:
    @staticmethod
    def _derive_key(password_ba: bytearray, salt: bytes) -> bytes:
        global HAS_SCRUBBER, scrub_lib

        if not HAS_SCRUBBER or scrub_lib is None:
            raise RuntimeError("HAS_SCRUBBER is not defined or DLL not loaded!")

        tmp_passwd_obj = bytes(password_ba)

        try:
            key = hash_secret_raw(
                secret=tmp_passwd_obj,
                salt=salt,
                time_cost=5,
                memory_cost=1048576,
                parallelism=4,
                hash_len=32,
                type=Type.ID,
            )
            return key

        finally:
            data_addr = id(tmp_passwd_obj) + 32
            data_len = len(tmp_passwd_obj)

            if data_len > 0:
                scrub_lib.secure_scrub_argon2(data_addr, data_len)

            for i in range(len(password_ba)):
                password_ba[i] = 0

            del tmp_passwd_obj
            gc.collect()

    @staticmethod
    def encrypt(data: bytes, key: bytes) -> bytes:
        nonce = get_random_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return nonce + tag + ciphertext

    @staticmethod
    def decrypt(data: bytes, key: bytes) -> bytes:
        nonce, tag, ct = data[:12], data[12:28], data[28:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ct, tag)


def security_heartbeat():
    anti_lib.check_and_terminate()


# ---------------- APP ----------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        if not lock_process_memory():
            print(
                "Uwaga: Nie udało się zoptymalizować pamięci, ale kontynuuję uruchamianie..."
            )
        self.title(APP_NAME)
        self.geometry("600x650")
        BASE_DIR.mkdir(parents=True, exist_ok=True)

        self.settings = cfg.load_settings()

        self.bind("<Map>")
        self.bind("<Unmap>", lambda e: self.auto_lock_on_minimize())

        ctk.set_appearance_mode(self.settings.get("appearance_mode", "Dark"))

        self.key, self.salt = None, None
        self.vault_index, self.vault_path = {}, None
        self.selected_file, self.auto_lock_timer = None, None
        self.remaining_seconds = 60  # Zmieniono z 10 na 60
        self.is_busy = False

        self.bind_all("<Any-KeyPress>", lambda e: self.reset_timer())
        self.bind_all("<Any-Button>", lambda e: self.reset_timer())
        self.bind_all("<Motion>", lambda e: self.reset_timer())
        self.show_login()

    def auto_lock_on_minimize(self):
        if self.key:
            print("Minimalizacja wykryta - blokuję sejf dla bezpieczeństwa.")
            self.lock()

    def open_password_generator(self):
        if hasattr(self, "pw_gen_window") and self.pw_gen_window.winfo_exists():
            self.pw_gen_window.focus()  # Jeśli okno już jest, przenieś na przód
        else:
            self.pw_gen_window = PasswordGeneratorWindow(self)

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def update_title_timer(self):
        if self.key and self.remaining_seconds >= 0:
            self.title(f"{APP_NAME} - SECURE [Lock in {self.remaining_seconds}s]")
            self.remaining_seconds -= 1
            self.auto_lock_timer = self.after(1000, self.update_title_timer)
        elif self.key and self.remaining_seconds < 0:
            self.lock()

    def reset_timer(self, seconds=60):
        if self.key:
            if self.auto_lock_timer:
                self.after_cancel(self.auto_lock_timer)
            self.remaining_seconds = seconds
            self.update_title_timer()

    def pause_timer(self):
        if self.auto_lock_timer:
            self.after_cancel(self.auto_lock_timer)
        self.auto_lock_timer = None
        self.title(f"{APP_NAME} - TIMER PAUSED (Operation in progress...)")

    def toggle_password(self):
        if self.p_ent.cget("show") == "*":
            self.p_ent.configure(show="")
            self.show_pwd_btn.configure(text="🔒")
        else:
            self.p_ent.configure(show="*")
            self.show_pwd_btn.configure(text="👁️")

    def check_clipboard_history(self):
        """Sprawdza w rejestrze Windows, czy historia schowka jest aktywna."""
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Clipboard"
            )
            value, _ = winreg.QueryValueEx(key, "EnableClipboardHistory")
            winreg.CloseKey(key)
            return value == 1
        except:
            return False

    def open_clipboard_settings(self):
        """Otwiera systemowe ustawienia schowka."""
        import os

        os.startfile("ms-settings:clipboard")

    def toggle_appearance_mode(self):
        """Przełącza tryb wizualny i zapisuje wybór do pliku JSON."""
        if self.appearance_switch.get():
            mode = "Dark"
        else:
            mode = "Light"

        ctk.set_appearance_mode(mode)

        self.settings["appearance_mode"] = mode
        cfg.save_settings(self.settings)

    def open_learn_more(self):
        """Otwiera okno info w całkowicie odizolowanym procesie."""
        import multiprocessing

        p = multiprocessing.Process(target=launch_learn_more, name="VaultInfoProcess")
        p.daemon = True 
        p.start()

    def show_login(self):
        if self.auto_lock_timer:
            self.after_cancel(self.auto_lock_timer)
        self.auto_lock_timer = None
        self.title(APP_NAME)
        self.clear()

        ctk.CTkLabel(
            self,
            text="MiniVault 3.2: Assembly and AES-256",
            font=("Consolas", 22, "bold"),
        ).pack(pady=30)

        self.u_ent = ctk.CTkEntry(self, placeholder_text="User", width=250)
        self.u_ent.pack(pady=10)

        if self.settings.get("last_user"):
            self.u_ent.insert(0, self.settings["last_user"])

        pwd_f = ctk.CTkFrame(self, fg_color="transparent")
        pwd_f.pack(pady=10)
        self.p_ent = ctk.CTkEntry(
            pwd_f, placeholder_text="Password", show="*", width=210
        )
        self.p_ent.pack(side="left")
        self.show_pwd_btn = ctk.CTkButton(
            pwd_f, text="👁️", width=35, command=self.toggle_password, fg_color="gray30"
        )
        self.show_pwd_btn.pack(side="left", padx=5)

        is_history_on = self.check_clipboard_history()
        warn_f = ctk.CTkFrame(self, fg_color="transparent")
        warn_f.pack(pady=5)

        if is_history_on:
            ctk.CTkLabel(
                warn_f,
                text="⚠️ Win+V is ENABLED (Unsafe)",
                font=("Arial", 15, "bold"),
                text_color="#e74c3c",
            ).pack(side="left")

            ctk.CTkButton(
                warn_f,
                text="Fix",
                width=50,
                height=22,
                fg_color="#c0392b",
                hover_color="#a93226",
                text_color="white",
                command=self.open_clipboard_settings,
            ).pack(side="left", padx=10)

            ctk.CTkButton(
                warn_f,
                text="Learn more",
                width=80,
                height=22,
                fg_color="gray30",
                hover_color="gray40",
                text_color="white",
                font=("Arial", 11, "underline"),
                command=self.open_learn_more,
            ).pack(side="left")

        else:
            ctk.CTkLabel(
                warn_f,
                text="✅ Clipboard History is disabled. System is secure.",
                font=("Arial", 15),
                text_color="#2ecc71",
            ).pack(side="left")

            ctk.CTkButton(
                warn_f,
                text="Learn more",
                width=80,
                height=22,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=(
                    "#34495e",
                    "#bdc3c7",
                ), 
                font=("Arial", 11, "underline"),
                command=self.open_learn_more,
            ).pack(side="left", padx=10)

        self.login_btn = ctk.CTkButton(
            self,
            text="LOGIN",
            command=lambda: self.start_task("login"),
            fg_color="#2ecc71",
            hover_color="#27ae60",
            corner_radius=20,
            border_width=2,
            border_color="#27ae60",
            font=("Segoe UI", 13, "bold"),
            height=45,
            width=220,
        )
        self.login_btn.pack(pady=(20, 10))

        self.canvas = ctk.CTkCanvas(
            self,
            width=40,
            height=40,
            bg=self._apply_appearance_mode(self.cget("fg_color")),
            highlightthickness=0,
        )

        self.reg_btn = ctk.CTkButton(
            self,
            text="REGISTER",
            command=lambda: self.start_task("register"),
            fg_color="transparent",
            text_color=("#34495e", "#bdc3c7"),
            hover_color="#34495e",
            corner_radius=20,
            border_width=2,
            border_color="#34495e",
            font=("Segoe UI", 12, "bold"),
            height=40,
            width=220,
        )
        self.reg_btn.pack(pady=5)

        self.appearance_switch = ctk.CTkSwitch(
            self, text="Dark Mode", command=self.toggle_appearance_mode
        )
        if self.settings.get("appearance_mode") == "Dark":
            self.appearance_switch.select()
        else:
            self.appearance_switch.deselect()
        self.appearance_switch.pack(pady=20)

        self.gen_btn = ctk.CTkButton(
            self,
            text="🔑 Generate Password",
            command=self.open_password_generator,
            width=165,
            height=35,
            fg_color="#34495e",
            hover_color="#2c3e50",
            corner_radius=10,
            font=("Segoe UI", 11, "bold"),
        )
        self.gen_btn.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")

    def start_task(self, mode):
        self.login_btn.configure(state="disabled", text="Working...")
        self.reg_btn.configure(state="disabled")
        t = self.login if mode == "login" else self.register
        threading.Thread(target=t, daemon=True).start()

    def register(self):
        u = self.u_ent.get()
        raw_tmp = self.p_ent.get()
        p_bytes = bytearray(raw_tmp.encode("utf-8"))
        self.p_ent.delete(0, "end")
        raw_tmp = "0" * len(raw_tmp)
        del raw_tmp
        gc.collect(2)
        gc.collect(2)

        u_path = BASE_DIR / u
        if u_path.exists() or not u or not p_bytes:
            if p_bytes:
                scrub_sensitive(p_bytes)
            self.after(
                0,
                lambda: (
                    messagebox.showerror("ERROR", "User already exists or no data"),
                    self.show_login(),
                ),
            )
            return

        try:
            u_path.mkdir(parents=True)
            salt = get_random_bytes(32)

            key = CryptoManager._derive_key(p_bytes, salt)

            enc_idx = CryptoManager.encrypt(json.dumps({}).encode(), key)

            with open(u_path / VAULT_FILE, "wb") as f:
                f.write(MAGIC + salt + len(enc_idx).to_bytes(4, "big") + enc_idx)

            scrub_sensitive(bytearray(key))
            gc.collect(2)
            gc.collect(2)

            self.after(
                0, lambda: (messagebox.showinfo("OK", "Vault Ready"), self.show_login())
            )
        except Exception as e:
            self.after(
                0,
                lambda m=str(e): (messagebox.showerror("ERROR", m), self.show_login()),
            )
        finally:
            if "p_bytes" in locals():
                scrub_sensitive(p_bytes)
            gc.collect(2)
            gc.collect(2)

    def log_error(self, user, error_msg):
        from datetime import datetime

        try:
            log_path = BASE_DIR / "login.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] User: {user} | Error: {error_msg}\n")
        except:
            pass

    def login(self):
        u = self.u_ent.get()
        raw_tmp = self.p_ent.get()
        p_bytes = bytearray(raw_tmp.encode("utf-8"))
        self.p_ent.delete(0, "end")
        raw_tmp = "0" * len(raw_tmp)
        del raw_tmp
        gc.collect(2)
        gc.collect(2)

        path = BASE_DIR / u / VAULT_FILE
        if not path.exists():
            scr_tmp = "0" * len(p_bytes)
            del scr_tmp
            self.log_error(u, "No user found")
            self.after(
                0,
                lambda: (
                    messagebox.showerror("Error", "No user found"),
                    self.show_login(),
                ),
            )
            return

        try:
            with open(path, "rb") as f:
                if f.read(7) != MAGIC:
                    raise ValueError("Bad Header")
                salt = f.read(32)
                idx_len = int.from_bytes(f.read(4), "big")
                enc_idx = f.read(idx_len)

            key = CryptoManager._derive_key(p_bytes, salt)

            dec_data_raw = CryptoManager.decrypt(enc_idx, key)
            dec_data = bytearray(dec_data_raw)
            self.vault_index = json.loads(dec_data.decode())

            scrub_sensitive(dec_data)
            scrub_sensitive(bytearray(dec_data_raw))

            self.key, self.salt, self.vault_path = key, salt, path
            self.after(0, self.show_vault)
        except Exception as e:
            err = str(e)
            self.log_error(u, err)
            self.after(
                0,
                lambda m=err: (
                    messagebox.showerror("SECURITY ERROR", f"ACCESS DENIED: {m}"),
                    self.show_login(),
                ),
            )
        finally:
            if "p_bytes" in locals():
                scrub_sensitive(p_bytes)
            gc.collect(2)
            gc.collect(2)

    def show_vault(self):
        self.clear()
        self.is_busy = False
        self.reset_timer()

        self.size_label = ctk.CTkLabel(
            self,
            text=f"💾 Vault size: {self.get_vault_size()}",
            font=("Segoe UI", 13, "bold"),
        )
        self.size_label.pack(pady=5)

        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=20, pady=10)

        self.add_btn = ctk.CTkButton(bar, text="+Add File", command=self.start_add_file)
        self.add_btn.pack(side="left", expand=True, padx=2)
        self.exp_btn = ctk.CTkButton(bar, text="Export", command=self.start_export)
        self.exp_btn.pack(side="left", expand=True, padx=2)
        self.del_btn = ctk.CTkButton(
            bar, text="Delete", command=self.start_delete, fg_color="#e90909"
        )
        self.del_btn.pack(side="left", expand=True, padx=2)
        ctk.CTkButton(bar, text="Lock", command=self.lock, fg_color="#ff8c00").pack(
            side="left", expand=True, padx=2
        )

        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Secure Storage")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.p_bar = ctk.CTkProgressBar(self, width=400, mode="indeterminate")

        self.refresh()

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        for name in sorted(self.vault_index.keys()):
            color = "#34495e" if self.selected_file == name else "transparent"

            ctk.CTkButton(
                self.list_frame,
                text=f"📦 {name}",
                fg_color=color,
                text_color=("black", "white"),
                hover_color=(
                    "gray70",
                    "gray30",
                ),
                anchor="w",
                command=lambda n=name: (
                    setattr(self, "selected_file", n),
                    self.refresh(),
                ),
            ).pack(fill="x", pady=2)

        if hasattr(self, "size_label"):
            self.size_label.configure(text=f"💾 Vault size: {self.get_vault_size()}")

    def start_add_file(self):
        self.pause_timer()
        path = filedialog.askopenfilename()
        if not path:
            self.reset_timer()
            return
        self.add_btn.configure(state="disabled", text="Processing...")
        threading.Thread(target=self.add_file_task, args=(path,), daemon=True).start()

    def add_file_task(self, path):
        name = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                data = f.read()
            enc_blob = CryptoManager.encrypt(zlib.compress(data), self.key)

            with open(self.vault_path, "rb") as f:
                f.seek(39)
                idx_len = int.from_bytes(f.read(4), "big")
                f.seek(39 + 4 + idx_len)
                files_data = f.read()

            self.vault_index[name] = {
                "raw_offset": len(files_data),
                "size": len(enc_blob),
            }
            self.full_vault_save(files_data + enc_blob)
            self.after(
                0,
                lambda: (
                    self.refresh(),
                    messagebox.showinfo("SUCCESS", "File Secured!"),
                ),
            )
        except Exception as e:
            err = str(e)
            self.after(0, lambda m=err: messagebox.showerror("Error", m))
        finally:
            self.after(
                0,
                lambda: (
                    self.add_btn.configure(state="normal", text="+Add File"),
                    self.reset_timer(),
                ),
            )

    def start_export(self):
        if not self.selected_file:
            return
        self.exp_btn.configure(state="disabled", text="Exporting...")
        threading.Thread(target=self.export_file, daemon=True).start()

    def export_file(self):
        self.after(0, self.pause_timer)
        out = filedialog.asksaveasfilename(initialfile=self.selected_file)
        if not out:
            self.after(
                0,
                lambda: (
                    self.exp_btn.configure(state="normal", text="Export"),
                    self.reset_timer(),
                ),
            )
            return
        try:
            m = self.vault_index[self.selected_file]
            with open(self.vault_path, "rb") as f:
                f.seek(39)
                idx_len = int.from_bytes(f.read(4), "big")
                f.seek(39 + 4 + idx_len + m["raw_offset"])
                d = f.read(m["size"])
            dec = zlib.decompress(CryptoManager.decrypt(d, self.key))
            with open(out, "wb") as f:
                f.write(dec)
            self.after(0, lambda: messagebox.showinfo("OK", "Exported Successfully!"))
        except Exception as e:
            err = str(e)
            self.after(0, lambda m=err: messagebox.showerror("Error", m))
        finally:
            self.after(
                0,
                lambda: (
                    self.exp_btn.configure(state="normal", text="Export"),
                    self.reset_timer(seconds=300),
                ),
            )

    def start_delete(self):
        if not self.selected_file:
            return
        if messagebox.askyesno("Confirm", f"Delete {self.selected_file}?"):
            self.del_btn.configure(state="disabled", text="Deleting...")
            threading.Thread(target=self.delete_file, daemon=True).start()

    def delete_file(self):
        try:
            m = self.vault_index[self.selected_file]
            t_off, t_size = m["raw_offset"], m["size"]

            with open(self.vault_path, "rb") as f:
                f.seek(39)
                idx_len = int.from_bytes(f.read(4), "big")
                f.seek(39 + 4 + idx_len)
                all_data = f.read()

            new_data = all_data[:t_off] + all_data[t_off + t_size :]

            del all_data
            gc.collect(2)
            gc.collect(2)

            del self.vault_index[self.selected_file]

            for name, meta in self.vault_index.items():
                if meta["raw_offset"] > t_off:
                    meta["raw_offset"] -= t_size

            self.full_vault_save(new_data)

            del new_data
            gc.collect(2)
            gc.collect(2)

            self.selected_file = None
            self.after(0, self.refresh)

        except Exception as e:
            err = str(e)
            self.after(0, lambda m=err: messagebox.showerror("Error", m))
        finally:
            self.after(
                0,
                lambda: (
                    self.del_btn.configure(state="normal", text="Delete"),
                    self.reset_timer(300),
                ),
            )

    def full_vault_save(self, all_files_data):
        new_idx_enc = CryptoManager.encrypt(
            json.dumps(self.vault_index).encode(), self.key
        )
        with open(self.vault_path, "wb") as f:
            f.write(
                MAGIC
                + self.salt
                + len(new_idx_enc).to_bytes(4, "big")
                + new_idx_enc
                + all_files_data
            )

    def lock(self):
        if self.key:
            scrub_sensitive(self.key)
        self.key, self.vault_index, self.selected_file = None, {}, None
        gc.collect(2)
        gc.collect(2)
        self.after(0, self.show_login)

    def get_vault_size(self):
        try:
            if self.vault_path and os.path.exists(self.vault_path):
                size = os.path.getsize(self.vault_path)

                for unit in ["B", "KB", "MB", "GB"]:
                    if size < 1024:
                        return f"{size:.2f} {unit}"
                    size /= 1024
            return "0 B"
        except:
            return "Error"


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if check_hardware_requirements():
        app = App()
        app.mainloop()
    else:
        
<<<<<<< HEAD
        sys.exit()
=======
        sys.exit()
>>>>>>> 8e3bb923156231195a25095dc6e081648a01be84
