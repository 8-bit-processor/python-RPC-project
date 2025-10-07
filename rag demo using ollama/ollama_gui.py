import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
from llm_parser import parse_note_with_ollama

class MedicalNoteParserGUI:
    def __init__(self, master):
        self.master = master
        master.title("Medical Note Parser (Ollama LLM)")

        # Configure grid weights for responsive layout
        master.grid_rowconfigure(0, weight=0)
        master.grid_rowconfigure(1, weight=1)
        master.grid_rowconfigure(2, weight=0)
        master.grid_rowconfigure(3, weight=1)
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)

        # --- Input Section ---
        self.input_label = tk.Label(master, text="Medical Note Input:")
        self.input_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        self.note_input = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=80, height=15)
        self.note_input.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        self.parse_button = tk.Button(master, text="Parse Note with Ollama", command=self.parse_note)
        self.parse_button.grid(row=2, column=0, columnspan=2, pady=10)

        # --- Output Section ---
        self.output_frame = tk.Frame(master)
        self.output_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        self.output_frame.grid_columnconfigure(0, weight=1)
        self.output_frame.grid_columnconfigure(1, weight=1)

        self.category_labels = {}
        self.category_text_widgets = {}

        categories = [
            "hpi", "medical_diagnosis", "past_surgical_history",
            "tobacco_use_history", "alcohol_and_illicit_use_history",
            "family_history", "ear_nose_and_throat_history",
            "cardiac_history", "pulmonary_history", "gastroenterology_history",
            "neurology_history", "musculoskeletal_history", "urology_history",
            "gynecology_history", "unknown_text"
        ]

        row_idx = 0
        col_idx = 0
        for category in categories:
            label_text = category.replace("_", " ").title() + ":"
            self.category_labels[category] = tk.Label(self.output_frame, text=label_text, anchor="w")
            self.category_labels[category].grid(row=row_idx, column=col_idx, sticky="w", padx=5, pady=2)

            self.category_text_widgets[category] = scrolledtext.ScrolledText(self.output_frame, wrap=tk.WORD, height=4, width=40, state=tk.DISABLED)
            self.category_text_widgets[category].grid(row=row_idx + 1, column=col_idx, sticky="nsew", padx=5, pady=2)

            col_idx = (col_idx + 1) % 2
            if col_idx == 0:
                row_idx += 2

        # Configure output frame rows/columns to expand
        for i in range(row_idx + 2):
            self.output_frame.grid_rowconfigure(i, weight=1)
        self.output_frame.grid_columnconfigure(0, weight=1)
        self.output_frame.grid_columnconfigure(1, weight=1)

    def parse_note(self):
        note_text = self.note_input.get("1.0", tk.END).strip()
        if not note_text:
            messagebox.showwarning("Input Error", "Please enter a medical note to parse.")
            return

        # Clear previous outputs
        for category in self.category_text_widgets:
            self.category_text_widgets[category].config(state=tk.NORMAL)
            self.category_text_widgets[category].delete("1.0", tk.END)
            self.category_text_widgets[category].config(state=tk.DISABLED)

        try:
            # Call the LLM parser
            parsed_data = parse_note_with_ollama(note_text, model_name="ollama3.2")

            for category, text_widget in self.category_text_widgets.items():
                content = parsed_data.get(category)
                if content:
                    text_widget.config(state=tk.NORMAL)
                    text_widget.insert(tk.END, content)
                    text_widget.config(state=tk.DISABLED)

            # Handle unknown_text separately if it's not explicitly in parsed_data
            # The LLM is instructed to return it, so it should be there.
            if "unknown_text" not in parsed_data:
                messagebox.showwarning("Parsing Warning", "'unknown_text' category not found in LLM output. Ensure LLM instructions are clear.")

        except Exception as e:
            messagebox.showerror("Parsing Error", f"An error occurred during parsing: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MedicalNoteParserGUI(root)
    root.mainloop()