import os
import easyocr
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import json
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import google.generativeai as genai
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# Supported Languages
SUPPORTED_LANGUAGES = {
    "English": "en",
    "Turkish": "tr",
    "Simplified Chinese": "ch_sim",
    "Japanese": "ja",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Russian": "ru",
}


class OCRApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OCR & Translation App")
        self.geometry("600x600")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.pdf_path = tk.StringVar()
        self.output_csv_path = tk.StringVar()
        self.output_json_path = tk.StringVar()
        self.gemini_api_key = tk.StringVar()  # Gemini API Key Input

        # Language Variables
        self.selected_lang1 = tk.StringVar(value="English")  # Default 1st language
        self.selected_lang2 = tk.StringVar(value="Turkish")  # Default 2nd language

        self.create_widgets()

    def create_widgets(self):
        """Creates UI elements"""

        ctk.CTkLabel(self, text="OCR & Translation", font=("Arial", 20)).pack(pady=10)

        # File selection
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(file_frame, text="PDF File:").pack(side="left", padx=5)
        ctk.CTkEntry(file_frame, textvariable=self.pdf_path, width=350).pack(side="left", padx=5)
        ctk.CTkButton(file_frame, text="Browse", command=self.select_pdf).pack(side="left", padx=5)

        # Output CSV Selection
        csv_frame = ctk.CTkFrame(self)
        csv_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(csv_frame, text="Output CSV:").pack(side="left", padx=5)
        ctk.CTkEntry(csv_frame, textvariable=self.output_csv_path, width=350).pack(side="left", padx=5)
        ctk.CTkButton(csv_frame, text="Browse", command=self.select_csv).pack(side="left", padx=5)

        # Output JSON Selection
        json_frame = ctk.CTkFrame(self)
        json_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(json_frame, text="Output JSON:").pack(side="left", padx=5)
        ctk.CTkEntry(json_frame, textvariable=self.output_json_path, width=350).pack(side="left", padx=5)
        ctk.CTkButton(json_frame, text="Browse", command=self.select_json).pack(side="left", padx=5)

        # Gemini API Key Input
        api_frame = ctk.CTkFrame(self)
        api_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(api_frame, text="Gemini API Key:").pack(side="left", padx=5)
        ctk.CTkEntry(api_frame, textvariable=self.gemini_api_key, width=350, show="*").pack(side="left", padx=5)

        # Language Selection
        lang_frame = ctk.CTkFrame(self)
        lang_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(lang_frame, text="Select OCR Languages:").pack(side="left", padx=5)

        self.lang1_menu = ctk.CTkOptionMenu(
            lang_frame, values=list(SUPPORTED_LANGUAGES.keys()), variable=self.selected_lang1
        )
        self.lang1_menu.pack(side="left", padx=5)

        self.lang2_menu = ctk.CTkOptionMenu(
            lang_frame, values=list(SUPPORTED_LANGUAGES.keys()), variable=self.selected_lang2
        )
        self.lang2_menu.pack(side="left", padx=5)

        # Start Button
        ctk.CTkButton(self, text="Start OCR", command=self.start_ocr, font=("Arial", 16)).pack(pady=15)

        # Log Output
        self.log_output = ctk.CTkTextbox(self, height=10)
        self.log_output.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, message):
        """Logs messages to the UI textbox."""
        self.log_output.insert("end", message + "\n")
        self.log_output.yview("end")

    def select_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.pdf_path.set(file_path)

    def select_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.output_csv_path.set(file_path)

    def select_json(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            self.output_json_path.set(file_path)

    def send_to_gemini(self, text):
        """Sends extracted text to Gemini AI for translation"""
        api_key = self.gemini_api_key.get()
        if not api_key:
            messagebox.showerror("Error", "Please enter your Gemini API key!")
            return ["Failed!"]

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        prompt = (
            "Extract words and their translations from the following text. "
            "Format the output as a JSON array of dictionaries with 'Word' and 'Translation' keys. "
            "Ensure the JSON is valid and properly formatted.\n\n"
            f"Text:\n{text}"
        )

        self.log("Sending text to AI...")
        response = model.generate_content(prompt)

        response_text = response.candidates[0].content.parts[0].text if response.candidates else ""
        json_data = response_text.split("```json\n")[1].split("\n```")[0] if "```json" in response_text else ""

        if not json_data:
            self.log("Failed to extract JSON from AI response!")
            return ["Failed!"]

        self.log("Processing AI response...")

        try:
            structured_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            self.log(f"JSON parsing error: {e}")
            structured_data = ["Failed!"]

        return structured_data

    def start_ocr(self):
        pdf_path = self.pdf_path.get()
        csv_output = self.output_csv_path.get()
        json_output = self.output_json_path.get()

        lang1 = SUPPORTED_LANGUAGES[self.selected_lang1.get()]
        lang2 = SUPPORTED_LANGUAGES[self.selected_lang2.get()]

        if lang1 in ["ch_sim", "ja"] and lang2 != "en":
            lang2 = "en"
        if lang2 in ["ch_sim", "ja"] and lang1 != "en":
            lang1 = "en"

        languages = [lang1, lang2]
        self.log(f"Selected OCR Languages: {languages}")

        reader = easyocr.Reader(languages, gpu=False)
        doc = fitz.open(pdf_path)
        raw_text = []

        for i, page in enumerate(doc):
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                img = Image.open(BytesIO(image_bytes))

                text = reader.readtext(img, detail=0)
                raw_text.append("\n".join(text))

        structured_data = self.send_to_gemini("\n".join(raw_text))

        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)
        self.log(f"JSON saved: {json_output}")

        self.log("OCR & AI processing completed!")


if __name__ == "__main__":
    app = OCRApp()
    app.mainloop()
