"""
Symptom Analyzer - Extracts and processes symptoms from user input
"""
import re
import json

class SymptomAnalyzer:
    def __init__(self):
        # Load medical knowledge base
        with open('medical_kb.json', 'r') as f:
            self.knowledge_base = json.load(f)
        
        # Common symptoms database
        self.symptoms_db = self.knowledge_base['symptoms']
        self.synonyms = self.knowledge_base['symptom_synonyms']
    
    def extract_symptoms(self, text):
        """
        Extract medical symptoms from natural language text
        """
        symptoms_found = []
        text_lower = text.lower()
        
        # Check for symptom patterns
        # Pattern 1: "I have [symptom]"
        have_pattern = r'i (?:have|am having|feel|am feeling) (?:a )?(?:severe |mild |slight |extreme )?([a-z]+(?: [a-z]+){0,3})'
        matches = re.findall(have_pattern, text_lower)
        for match in matches:
            symptom = self.normalize_symptom(match)
            if symptom:
                symptoms_found.append(symptom)
        
        # Pattern 2: "[symptom] pain/ache/etc"
        symptom_words = ['pain', 'ache', 'fever', 'cough', 'headache', 'nausea']
        for word in symptom_words:
            if word in text_lower:
                # Get context (2 words before)
                words = text_lower.split()
                for i, w in enumerate(words):
                    if w == word and i > 0:
                        context = ' '.join(words[max(0, i-2):i+1])
                        symptom = self.normalize_symptom(context)
                        if symptom:
                            symptoms_found.append(symptom)
        
        # Pattern 3: Direct symptom matching
        for symptom, info in self.symptoms_db.items():
            if any(keyword in text_lower for keyword in info['keywords']):
                symptoms_found.append(symptom)
        
        # Remove duplicates
        return list(set(symptoms_found))[:10]  # Limit to 10 symptoms
    
    def normalize_symptom(self, symptom_text):
        """
        Convert symptom description to standardized term
        """
        symptom_text = symptom_text.strip()
        
        # Check synonyms first
        for std_term, synonyms in self.synonyms.items():
            if symptom_text in synonyms or any(syn in symptom_text for syn in synonyms):
                return std_term
        
        # Direct match in symptoms database
        for symptom in self.symptoms_db:
            if symptom in symptom_text or symptom_text in symptom:
                return symptom
        
        return symptom_text if len(symptom_text.split()) <= 3 else None
    
    def get_symptom_info(self, symptom):
        """
        Get detailed information about a symptom
        """
        return self.symptoms_db.get(symptom, {
            'description': 'General symptom',
            'urgency': 'moderate',
            'common_causes': ['Various causes'],
            'first_aid': ['Rest', 'Consult doctor']
        })
