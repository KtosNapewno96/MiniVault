import customtkinter as ctk


class LearnMoreWindow(ctk.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # --- Ustawienia systemowe okna ---
        self.title("MiniVault Security Briefing")
        self.resizable(False, False)

        # Ukrywamy okno na czas obliczeń pozycji, żeby nie "skakało"
        self.withdraw()

        # --- Kolory i Design ---
        brand_red = "#e74c3c"
        brand_green = "#2ecc71"

        # --- GŁÓWNY KONTENER ---
        self.main_frame = ctk.CTkFrame(
            self, corner_radius=20, border_width=2, border_color=("gray80", "gray30")
        )
        self.main_frame.pack(padx=15, pady=15, fill="both", expand=True)

        # --- NAGŁÓWEK (Baner Ostrzegawczy) ---
        self.header_frame = ctk.CTkFrame(
            self.main_frame, fg_color=brand_red, corner_radius=15, height=70
        )
        self.header_frame.pack(fill="x", padx=12, pady=(12, 10))
        self.header_frame.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="⚠ Windows Clipboard (Win+V) Risk",
            font=("Consolas", 20, "bold"),
            text_color="white",
        )
        self.title_label.pack(expand=True)

        # --- SEKCJA TREŚCI (Scrollable) ---
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_frame, fg_color="transparent", height=340
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=12)

        # Bloki informacyjne
        self._add_info_block(
            "📍 WHAT IS WINDOWS HISTORY?",
            "Windows 10/11 includes a 'Clipboard History' tool (Win+V). It records every text "
            "string you copy, creating a permanent log of your decrypted passwords.",
        )

        self._add_info_block(
            "⚠️ THE LEAK VECTOR",
            "Even if MiniVault clears the current clipboard, the OS might have already "
            "cached the data in its internal history service. This data is stored in "
            "plain text and can be synced to your Microsoft Cloud account.",
        )

        self._add_info_block(
            "🛡️ MINIVAULT COUNTERMEASURES",
            "Version 3.2.0 uses aggressive 'Scrub-and-Clean' memory protocols. However, "
            "system-level logging (Win+V) happens outside the application's control.",
        )

        self._add_info_block(
            "✅ ACTION REQUIRED",
            "1. Click the 'Fix' button in MiniVault.\n"
            "2. Turn OFF 'Clipboard History' in Windows Settings.\n"
            "3. Clear existing history to wipe previous secrets.",
        )

        # --- STOPKA / PRZYCISK Z TIMEREM ---
        self.countdown = 3  # Czas odliczania w sekundach

        self.footer_btn = ctk.CTkButton(
            self.main_frame,
            text=f"PLEASE READ ({self.countdown}s)",
            command=self.destroy,
            fg_color="gray40",
            state="disabled",
            hover_color="#27ae60",
            font=("Consolas", 14, "bold"),
            height=45,
            corner_radius=12,
        )
        self.footer_btn.pack(pady=15, padx=40, fill="x")

        # --- FINALIZE WINDOW ---
        self._set_geometry(520, 600)
        self.deiconify()  # Pokazujemy okno po ustawieniu pozycji

        # Uruchomienie odliczania
        self.update_button_timer()

    def update_button_timer(self):
        """Obsługa odliczania na przycisku akceptacji."""
        if self.countdown > 0:
            self.footer_btn.configure(text=f"PLEASE READ ({self.countdown}s)")
            self.countdown -= 1
            self.after(1000, self.update_button_timer)
        else:
            self.footer_btn.configure(
                state="normal",
                text="I ACKNOWLEDGE THE RISK",
                fg_color="#2ecc71",  # brand_green
            )

    def _add_info_block(self, title, text):
        block_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=("gray95", "gray17"),
            corner_radius=12,
            border_width=1,
            border_color=("gray85", "gray25"),
        )
        block_frame.pack(fill="x", pady=8, padx=5)

        t_label = ctk.CTkLabel(
            block_frame,
            text=title,
            font=("Consolas", 13, "bold"),
            text_color=("#c0392b", "#ff7675"),
        )
        t_label.pack(anchor="w", padx=15, pady=(10, 5))

        b_label = ctk.CTkLabel(
            block_frame,
            text=text,
            font=("Consolas", 12),
            justify="left",
            wraplength=400,
            text_color=("black", "white"),
        )
        b_label.pack(anchor="w", padx=15, pady=(0, 10))

    def _set_geometry(self, width, height):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        if y < 60:
            y = 60  # Zabezpieczenie przed ucieczką za górę
        self.geometry(f"{width}x{height}+{x}+{y}")
