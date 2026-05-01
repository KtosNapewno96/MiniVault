import ctypes
from ctypes import wintypes
import platform
from platform import system
import re
import sys
import psutil
from tkinter import filedialog, messagebox

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


# Definiujemy precyzyjnie typy dla WinAPI, żeby uniknąć błędu 6
kernel32.SetProcessWorkingSetSize.argtypes = [
    wintypes.HANDLE,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
kernel32.SetProcessWorkingSetSize.restype = wintypes.BOOL


def lock_process_memory():
    if platform.system() == "Windows":
        # -1 to stała oznaczająca bieżący proces (pseudohandle)
        current_process_handle = wintypes.HANDLE(-1)

        min_size = 1 * 1024 * 1024
        max_size = 4 * 1024 * 1024 * 1024

        if not kernel32.SetProcessWorkingSetSize(
            current_process_handle, min_size, max_size
        ):
            err = kernel32.GetLastError()  # lub ctypes.get_last_error()
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
APP_NAME = "MiniVault 3.1"
local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
BASE_DIR = Path(local_appdata) / "Programs" / APP_NAME
VAULT_FILE = "vault.mvault"
MAGIC = b"AES-256"


# ---------------- MEMORY SECURITY ----------------
def scrub_sensitive(obj):
    # bytearray – to jest super, bo mutowalne bajty faktycznie zerujemy w RAM
    if isinstance(obj, bytearray):
        for i in range(len(obj)):
            obj[i] = 0

    # lista – zerujemy elementy
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = 0

    # Wymuszenie sprzątania (musi być po if-ach, z poprawnym wcięciem)
    gc.collect()

    # Próba usunięcia referencji
    try:
        del obj
    except:
        pass


# ---------------- CRYPTOGRAPHY ----------------
class CryptoManager:
    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        pwd_bytes = password.encode()
        key = hash_secret_raw(
            secret=pwd_bytes,
            salt=salt,
            time_cost=5,
            memory_cost=1048576,
            parallelism=4,
            hash_len=32,
            type=Type.ID,
        )
        scrub_sensitive(pwd_bytes)
        return key

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

        self.key, self.salt = None, None
        self.vault_index, self.vault_path = {}, None
        self.selected_file, self.auto_lock_timer = None, None
        self.remaining_seconds = 60  # Zmieniono z 10 na 60
        self.is_busy = False

        self.bind_all("<Any-KeyPress>", lambda e: self.reset_timer())
        self.bind_all("<Any-Button>", lambda e: self.reset_timer())
        self.bind_all("<Motion>", lambda e: self.reset_timer())
        self.show_login()

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

    def reset_timer(self, seconds=60):  # Domyślnie 60s przy ruchu myszką
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
        """Przełącza tryb Dark/Light."""
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

    def show_login(self):
        if self.auto_lock_timer:
            self.after_cancel(self.auto_lock_timer)
        self.auto_lock_timer = None
        self.title(APP_NAME)
        self.clear()

        # Tytuł
        ctk.CTkLabel(
            self,
            text="🛡️ MiniVault: AES-256 and Argon2id with Python",
            font=("Arial", 22, "bold"),
        ).pack(pady=30)

        # Pole użytkownika
        self.u_ent = ctk.CTkEntry(self, placeholder_text="User", width=250)
        self.u_ent.pack(pady=10)

        # Pole hasła z okiem
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

        # --- DYNAMICZNY ALERT SCHOWKA (Win+V) ---
        is_history_on = self.check_clipboard_history()
        if is_history_on:
            warn_f = ctk.CTkFrame(self, fg_color="transparent")
            warn_f.pack(pady=5)
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
                command=self.open_clipboard_settings,
            ).pack(side="left", padx=10)
        else:
            ctk.CTkLabel(
                self,
                text="✅ Clipboard History is disabled. System is secure.",
                font=("Arial", 15),
                text_color="#2ecc71",
            ).pack(pady=5)

        # Przycisk Logowania z efektem Primary
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

        # Przycisk Rejestracji
        self.reg_btn = ctk.CTkButton(
            self,
            text="REGISTER",
            command=lambda: self.start_task("register"),
            fg_color="transparent",
            text_color=("#34495e", "#bdc3c7"),  # Kolor dostosowany do trybu Light/Dark
            hover_color="#34495e",
            corner_radius=20,
            border_width=2,
            border_color="#34495e",
            font=("Segoe UI", 12, "bold"),
            height=40,
            width=220,
        )
        self.reg_btn.pack(pady=5)

        # --- PRZEŁĄCZNIK TRYBU CIEMNEGO ---
        self.appearance_switch = ctk.CTkSwitch(
            self, text="Dark Mode", command=self.toggle_appearance_mode
        )
        # Ustawiamy pozycję switcha na starcie
        if ctk.get_appearance_mode() == "Dark":
            self.appearance_switch.select()
        self.appearance_switch.pack(pady=20)

    def start_task(self, mode):
        self.login_btn.configure(state="disabled", text="Working...")
        self.reg_btn.configure(state="disabled")
        t = self.login if mode == "login" else self.register
        threading.Thread(target=t, daemon=True).start()

    def register(self):
        u, p = self.u_ent.get(), self.p_ent.get()
        u_path = BASE_DIR / u
        if u_path.exists() or not u or not p:
            self.after(
                0,
                lambda: (
                    messagebox.showerror("ERROR", "User exists or data empty"),
                    self.show_login(),
                ),
            )
            return
        try:
            u_path.mkdir(parents=True)
            salt = get_random_bytes(32)
            key = CryptoManager.derive_key(p, salt)
            enc_idx = CryptoManager.encrypt(json.dumps({}).encode(), key)
            with open(u_path / VAULT_FILE, "wb") as f:
                f.write(MAGIC + salt + len(enc_idx).to_bytes(4, "big") + enc_idx)
            self.after(
                0, lambda: (messagebox.showinfo("OK", "Vault Ready"), self.show_login())
            )
        except Exception as e:
            err = str(e)
            self.after(
                0, lambda m=err: (messagebox.showerror("ERROR", m), self.show_login())
            )

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
        u, p = self.u_ent.get(), self.p_ent.get()
        path = BASE_DIR / u / VAULT_FILE
        if not path.exists():
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
            key = CryptoManager.derive_key(p, salt)
            self.vault_index = json.loads(CryptoManager.decrypt(enc_idx, key).decode())
            self.key, self.salt, self.vault_path = key, salt, path
            self.after(0, self.show_vault)
        except Exception as e:
            err = str(e)

            self.log_error(u, err)

            p_bytes = p.encode()
            scrub_sensitive(p_bytes)
            p = None
            gc.collect()

            self.after(
                0,
                lambda m=err: (
                    messagebox.showerror("SECURITY ERROR", f"ACCESS DENIED: {m}"),
                    self.show_login(),
                ),
            )

    def show_vault(self):
        self.clear()
        self.is_busy = False
        self.reset_timer()

        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=20, pady=10)

        self.add_btn = ctk.CTkButton(bar, text="+Add File", command=self.start_add_file)
        self.add_btn.pack(side="left", expand=True, padx=2)
        self.exp_btn = ctk.CTkButton(bar, text="Export", command=self.start_export)
        self.exp_btn.pack(side="left", expand=True, padx=2)
        self.del_btn = ctk.CTkButton(
            bar, text="Delete", command=self.start_delete, fg_color="#e67e22"
        )
        self.del_btn.pack(side="left", expand=True, padx=2)
        ctk.CTkButton(bar, text="Lock", command=self.lock, fg_color="#c0392b").pack(
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
                anchor="w",
                command=lambda n=name: (
                    setattr(self, "selected_file", n),
                    self.refresh(),
                ),
            ).pack(fill="x", pady=2)

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
            gc.collect()

            del self.vault_index[self.selected_file]

            for name, meta in self.vault_index.items():
                if meta["raw_offset"] > t_off:
                    meta["raw_offset"] -= t_size

            self.full_vault_save(new_data)

            del new_data
            gc.collect()

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
        gc.collect()
        self.after(0, self.show_login)


if __name__ == "__main__":
    # 1. Najpierw sprawdzamy sprzęt
    if check_hardware_requirements():
        # 2. Jeśli sprzęt jest OK, tworzymy okno (teraz zadziała, bo klasa App jest wyżej)
        app = App()
        app.mainloop()
    else:
        # 3. Jeśli sprzęt za słaby, zamykamy wszystko
        sys.exit()
