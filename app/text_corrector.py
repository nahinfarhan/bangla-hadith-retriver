import re
from typing import Dict, List, Tuple

class IslamicFactChecker:
    def __init__(self):
        self.islamic_facts = {
            # Pillars of Islam
            "ইসলামের ভিত্তি": 5,
            "ইসলামের স্তম্ভ": 5,
            "ইসলামের রুকন": 5,
            
            # Pillars of Iman
            "ঈমানের ভিত্তি": 6,
            "ঈমানের স্তম্ভ": 6,
            "ঈমানের রুকন": 6,
            
            # Prayer times
            "নামাজ": 5,
            "সালাত": 5,
            "ফরজ নামাজ": 5,
            
            # Other Islamic facts
            "কালিমা": 6,
            "খলিফা": 4,  # Rashidun Caliphs
        }
        
        self.number_patterns = {
            "এক": 1, "একটি": 1, "১": 1,
            "দুই": 2, "দুটি": 2, "২": 2,
            "তিন": 3, "তিনটি": 3, "৩": 3,
            "চার": 4, "চারটি": 4, "৪": 4,
            "পাঁচ": 5, "পাঁচটি": 5, "৫": 5,
            "ছয়": 6, "ছয়টি": 6, "৬": 6,
            "সাত": 7, "সাতটি": 7, "৭": 7,
            "আট": 8, "আটটি": 8, "৮": 8,
            "নয়": 9, "নয়টি": 9, "৯": 9,
            "দশ": 10, "দশটি": 10, "১০": 10,
            "বিশ": 20, "বিশটি": 20, "২০": 20,
            "ত্রিশ": 30, "ত্রিশটি": 30, "৩০": 30,
            "চল্লিশ": 40, "চল্লিশটি": 40, "৪০": 40,
            "পঞ্চাশ": 50, "পঞ্চাশটি": 50, "৫০": 50,
            "ষাট": 60, "ষাটটি": 60, "৬০": 60,
        }
    
    def extract_islamic_claims(self, text: str) -> List[Tuple[str, int, int]]:
        """Extract Islamic numerical claims from text"""
        claims = []
        
        for concept, correct_number in self.islamic_facts.items():
            # Look for patterns like "ইসলামের ভিত্তি পাঁচটি" or "ইসলামের ভিত্তি ৫টি"
            pattern = rf"{re.escape(concept)}\s*([\w\d]+)\s*টি?"
            matches = re.findall(pattern, text)
            
            for match in matches:
                found_number = self.number_patterns.get(match, None)
                if found_number:
                    claims.append((concept, found_number, correct_number))
        
        return claims
    
    def validate_text(self, text: str) -> Dict:
        """Validate Islamic facts in text"""
        claims = self.extract_islamic_claims(text)
        
        result = {
            "has_islamic_content": len(claims) > 0,
            "claims": [],
            "errors_found": 0,
            "corrections_needed": False
        }
        
        for concept, found_num, correct_num in claims:
            is_correct = found_num == correct_num
            claim_result = {
                "concept": concept,
                "found_number": found_num,
                "correct_number": correct_num,
                "is_correct": is_correct,
                "message": f"{concept} সংখ্যা {'সঠিক' if is_correct else 'ভুল'} - সঠিক সংখ্যা {correct_num}"
            }
            result["claims"].append(claim_result)
            
            if not is_correct:
                result["errors_found"] += 1
                result["corrections_needed"] = True
        
        return result
    
    def correct_text(self, text: str) -> str:
        """Apply corrections to Islamic facts"""
        corrected_text = text
        claims = self.extract_islamic_claims(text)
        
        for concept, found_num, correct_num in claims:
            if found_num != correct_num:
                # Find the correct Bangla number word
                correct_word = None
                for word, num in self.number_patterns.items():
                    if num == correct_num and "টি" not in word:
                        correct_word = word + "টি"
                        break
                
                if correct_word:
                    # Replace the incorrect number
                    for word, num in self.number_patterns.items():
                        if num == found_num:
                            pattern = rf"{re.escape(concept)}\s*{re.escape(word)}\s*টি?"
                            replacement = f"{concept} {correct_word}"
                            corrected_text = re.sub(pattern, replacement, corrected_text)
        
        return corrected_text