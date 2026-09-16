import pdfplumber
import re
import os
from typing import Tuple, Dict, Optional
import unicodedata

class HadithPDFProcessor:
    """
    Specialized processor for Hadith PDFs from hadithbd.com
    - Extracts Bangla text only
    - Removes Arabic text, page numbers, headers/footers
    - One PDF = One complete Hadith
    """
    
    def __init__(self):
        # Patterns to remove
        self.patterns_to_remove = [
            r'hadithbd\.com',  # Website name
            r'—\s*সহীহ\s*বুখারী\s*\(তাওহীদ\s*পাবঃ\)',  # Header
            r'সহীহ\s*বুখারী\s*\(তাওহীদ\s*পাবঃ\)',  # Alternative header
            r'\d+/\d+',  # Page numbers like 1/6, 2/6
            r'^\d+$',  # Standalone page numbers
            r'Link\s*—\s*https?://[^\s]+',  # Links
            r'হাদিসবিডির\s*প্রজেক্টে\s*অনুদান\s*দিন',  # Donation text
            r'পাবলিশারঃ\s*তাওহীদ\s*পাবলিকেশন',  # Publisher
            r'বর্ণনাকারীঃ.*?(?=\n|$)',  # Narrator line
            r'হাদিসের\s*মান:\s*সহিহ.*?(?=\n|$)',  # Hadith grade
            r'পুনঃনিরীক্ষিত',  # Re-verified text
        ]
        
        # Arabic Unicode ranges
        self.arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+'
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from PDF with better encoding handling"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Try different extraction methods
                    page_text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=2)
                    if not page_text:
                        # Fallback to default extraction
                        page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise Exception(f"Error extracting PDF: {str(e)}")
        
        return text.strip()
    
    def remove_arabic_text(self, text: str) -> str:
        """Remove all Arabic text"""
        # Remove Arabic characters and their diacritics
        text = re.sub(self.arabic_pattern, '', text)
        return text
    
    def remove_unwanted_patterns(self, text: str) -> str:
        """Remove page numbers, headers, footers, and website info"""
        for pattern in self.patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        return text
    
    def clean_bangla_text(self, text: str) -> str:
        """Clean and normalize Bangla text"""
        # Normalize Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Remove corrupted patterns
        text = re.sub(r'\(cid:\d+\)', '', text)
        text = re.sub(r'[\ufeff\u200b-\u200f\u202a-\u202e]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Fix common Bangla PDF extraction issues
        bangla_fixes = {
            r'পৰ্': 'প্র',
            r'েক': 'কে',
            r'েথ': 'থে',
            r'েদ': 'দে',
            r'েব': 'বে',
            r'েল': 'লে',
            r'েন': 'নে',
            r'েস': 'সে',
            r'েত': 'তে',
            r'েয়': 'যে',
            r'েশ': 'শে',
            r'েফ': 'ফে',
            r'েম': 'মে',
            r'েহ': 'হে',
            r'েগ': 'গে',
            r'েচ': 'চে',
            r'েজ': 'জে',
            r'েখ': 'খে',
            r'েপ': 'পে',
            r'েভ': 'ভে',
            r'ের': 'রে',
        }
        
        for wrong, correct in bangla_fixes.items():
            text = re.sub(wrong, correct, text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        
        return '\n'.join(lines)
    
    def extract_hadith_metadata(self, filename: str, text: str) -> Dict[str, any]:
        """Extract metadata from filename and text"""
        metadata = {
            'filename': filename,
            'book': 'Unknown',
            'hadith_number': None,
            'word_count': len(text.split()),
            'char_count': len(text),
        }
        
        # Extract book name and hadith number from filename
        # Example: Sahih-al-Bukhari-hadith-1.pdf
        match = re.search(r'(.*?)-hadith-(\d+)', filename)
        if match:
            metadata['book'] = match.group(1).replace('-', ' ').title()
            metadata['hadith_number'] = int(match.group(2))
        
        # Try to extract hadith number from text if not in filename
        if not metadata['hadith_number']:
            number_match = re.search(r'হাদিস\s*নাম্বারঃ?\s*(\d+)', text)
            if number_match:
                metadata['hadith_number'] = int(number_match.group(1))
        
        return metadata
    
    def process_hadith_pdf(self, pdf_path: str) -> Tuple[str, Dict[str, any]]:
        """
        Main processing function: PDF -> Clean Bangla Hadith Text
        Returns: (cleaned_text, metadata)
        """
        filename = os.path.basename(pdf_path)
        
        # Step 1: Extract raw text
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        if not raw_text.strip():
            raise ValueError(f"No text extracted from {filename}")
        
        # Step 2: Remove Arabic text
        text_no_arabic = self.remove_arabic_text(raw_text)
        
        # Step 3: Remove unwanted patterns
        text_cleaned = self.remove_unwanted_patterns(text_no_arabic)
        
        # Step 4: Clean Bangla text
        final_text = self.clean_bangla_text(text_cleaned)
        
        if not final_text.strip():
            raise ValueError(f"No Bangla text remaining after cleaning in {filename}")
        
        # Step 5: Extract metadata
        metadata = self.extract_hadith_metadata(filename, final_text)
        
        return final_text, metadata
    
    def validate_output(self, text: str, metadata: Dict) -> bool:
        """Validate that the output is reasonable"""
        # Check minimum length
        if len(text.split()) < 10:
            return False
        
        # Check that it contains Bangla characters
        bangla_pattern = r'[\u0980-\u09FF]+'
        if not re.search(bangla_pattern, text):
            return False
        
        # Check that Arabic is removed
        if re.search(self.arabic_pattern, text):
            return False
        
        return True
