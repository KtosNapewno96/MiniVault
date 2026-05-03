<<<<<<< HEAD
import secrets
import string
import gc
import ctypes
import sys
from pathlib import Path
from tkinter import messagebox
import pyperclip
import customtkinter as ctk

LIB_PATH = Path(__file__).parent / "scrub.dll"

if not LIB_PATH.exists():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("CRITICAL ERROR", f"ACCESS DENIED: 'scrub.dll' not found!")
    sys.exit(1)

try:
    scrub_lib = ctypes.CDLL(str(LIB_PATH))
    scrub_lib.secure_scrub_memory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    scrub_lib.secure_scrub_memory.restype = None
except Exception as e:
    messagebox.showerror("DLL Load Error", f"Failed to load scrub.dll:\n{str(e)}")
    sys.exit(1)


def asm_scrub(data):
    """Bezpośrednie zerowanie RAM za pomocą skompilowanego ASM."""
    if isinstance(data, bytearray):
        addr = ctypes.addressof((ctypes.c_char * len(data)).from_buffer(data))
        scrub_lib.secure_scrub_memory(addr, len(data))
    elif isinstance(data, str) and data:
        addr = id(data) + 32
        scrub_lib.secure_scrub_memory(addr, len(data))


def generate_secure_password_raw(length=64):
    alphabet = (string.ascii_letters + string.digits + string.punctuation).encode()
    pwd = bytearray(secrets.choice(alphabet) for _ in range(length))
    return pwd


class PasswordGeneratorWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Secure Generator (ASM LOCKED)")
        self.geometry("500x320")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(
            self.frame,
            text="Generated Password:",
            font=("Segoe UI", 14, "bold"),
            text_color=("black", "white"),
        )
        self.label.pack(pady=(20, 5))

        self.pwd_entry = ctk.CTkEntry(
            self.frame, width=400, height=40, font=("Consolas", 12), show="*"
        )
        self.pwd_entry.pack(pady=10, padx=20)

        self.btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.btn_frame.pack(pady=20)

        self.gen_btn = ctk.CTkButton(
            self.btn_frame, text="🔄 Generate", command=self.generate, width=120
        )
        self.gen_btn.grid(row=0, column=0, padx=5)

        self.show_btn = ctk.CTkButton(
            self.btn_frame,
            text="👁️ Show",
            command=self.toggle_visibility,
            width=120,
            fg_color="gray",
        )
        self.show_btn.grid(row=0, column=1, padx=5)

        self.copy_btn = ctk.CTkButton(
            self.btn_frame,
            text="📋 Copy",
            command=self.copy_to_clipboard,
            width=120,
            fg_color="#2c3e50",
        )
        self.copy_btn.grid(row=0, column=2, padx=5)

    def generate(self):
        pwd_bytes = generate_secure_password_raw(64)
        pwd_str = pwd_bytes.decode()

        self.pwd_entry.delete(0, "end")
        self.pwd_entry.insert(0, pwd_str)

        asm_scrub(pwd_bytes)
        asm_scrub(pwd_str)
        gc.collect(2)
        gc.collect(2)

    def toggle_visibility(self):
        if self.pwd_entry.cget("show") == "*":
            self.pwd_entry.configure(show="")
            self.show_btn.configure(text="🔒 Hide")
        else:
            self.pwd_entry.configure(show="*")
            self.show_btn.configure(text="👁️ Show")

    def copy_to_clipboard(self):
        raw_pwd = self.pwd_entry.get()
        if raw_pwd:
            pyperclip.copy(raw_pwd)
            self.copy_btn.configure(text="✅ Copied!", fg_color="green")

            asm_scrub(raw_pwd)

            self.after(10000, self.secure_clear_clipboard)
            self.after(
                2000,
                lambda: self.copy_btn.configure(text="📋 Copy", fg_color="#2c3e50"),
            )

    def secure_clear_clipboard(self):
        try:
            pyperclip.copy("")
            self.clipboard_clear()
            self.clipboard_append("DEADBEEF")
            self.clipboard_clear()
        except:
            pass

    def on_close(self):
        content = self.pwd_entry.get()
        if content:
            asm_scrub(content)
        self.pwd_entry.delete(0, "end")
        gc.collect(0)
        gc.collect(1)
        gc.collect(2)
        self.destroy()
=======
import secrets
import string
import gc
import ctypes
import sys
from pathlib import Path
from tkinter import messagebox
import pyperclip
import customtkinter as ctk

LIB_PATH = Path(__file__).parent / "scrub.dll"

if not LIB_PATH.exists():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("CRITICAL ERROR", f"ACCESS DENIED: 'scrub.dll' not found!")
    sys.exit(1)

try:
    scrub_lib = ctypes.CDLL(str(LIB_PATH))
    scrub_lib.secure_scrub_memory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    scrub_lib.secure_scrub_memory.restype = None
except Exception as e:
    messagebox.showerror("DLL Load Error", f"Failed to load scrub.dll:\n{str(e)}")
    sys.exit(1)


def asm_scrub(data):
    """Bezpośrednie zerowanie RAM za pomocą skompilowanego ASM."""
    if isinstance(data, bytearray):
        addr = ctypes.addressof((ctypes.c_char * len(data)).from_buffer(data))
        scrub_lib.secure_scrub_memory(addr, len(data))
    elif isinstance(data, str) and data:
        addr = id(data) + 32
        scrub_lib.secure_scrub_memory(addr, len(data))


def generate_secure_password_raw(length=64):
    alphabet = (string.ascii_letters + string.digits + string.punctuation).encode()
    pwd = bytearray(secrets.choice(alphabet) for _ in range(length))
    return pwd


class PasswordGeneratorWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Secure Generator (ASM LOCKED)")
        self.geometry("500x320")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(
            self.frame,
            text="Generated Password:",
            font=("Segoe UI", 14, "bold"),
            text_color=("black", "white"),
        )
        self.label.pack(pady=(20, 5))

        self.pwd_entry = ctk.CTkEntry(
            self.frame, width=400, height=40, font=("Consolas", 12), show="*"
        )
        self.pwd_entry.pack(pady=10, padx=20)

        self.btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.btn_frame.pack(pady=20)

        self.gen_btn = ctk.CTkButton(
            self.btn_frame, text="🔄 Generate", command=self.generate, width=120
        )
        self.gen_btn.grid(row=0, column=0, padx=5)

        self.show_btn = ctk.CTkButton(
            self.btn_frame,
            text="👁️ Show",
            command=self.toggle_visibility,
            width=120,
            fg_color="gray",
        )
        self.show_btn.grid(row=0, column=1, padx=5)

        self.copy_btn = ctk.CTkButton(
            self.btn_frame,
            text="📋 Copy",
            command=self.copy_to_clipboard,
            width=120,
            fg_color="#2c3e50",
        )
        self.copy_btn.grid(row=0, column=2, padx=5)

    def generate(self):
        pwd_bytes = generate_secure_password_raw(64)
        pwd_str = pwd_bytes.decode()

        self.pwd_entry.delete(0, "end")
        self.pwd_entry.insert(0, pwd_str)

        asm_scrub(pwd_bytes)
        asm_scrub(pwd_str)
        gc.collect(2)
        gc.collect(2)

    def toggle_visibility(self):
        if self.pwd_entry.cget("show") == "*":
            self.pwd_entry.configure(show="")
            self.show_btn.configure(text="🔒 Hide")
        else:
            self.pwd_entry.configure(show="*")
            self.show_btn.configure(text="👁️ Show")

    def copy_to_clipboard(self):
        raw_pwd = self.pwd_entry.get()
        if raw_pwd:
            pyperclip.copy(raw_pwd)
            self.copy_btn.configure(text="✅ Copied!", fg_color="green")

            asm_scrub(raw_pwd)

            self.after(10000, self.secure_clear_clipboard)
            self.after(
                2000,
                lambda: self.copy_btn.configure(text="📋 Copy", fg_color="#2c3e50"),
            )

    def secure_clear_clipboard(self):
        try:
            pyperclip.copy("")
            self.clipboard_clear()
            self.clipboard_append("DEADBEEF")
            self.clipboard_clear()
        except:
            pass

    def on_close(self):
        content = self.pwd_entry.get()
        if content:
            asm_scrub(content)
        self.pwd_entry.delete(0, "end")
        gc.collect(0)
        gc.collect(1)
        gc.collect(2)
        self.destroy()
>>>>>>> 8e3bb923156231195a25095dc6e081648a01be84
