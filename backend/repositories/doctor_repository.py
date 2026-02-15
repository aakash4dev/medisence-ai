import json
from typing import List, Dict, Optional

class DoctorRepository:
    def __init__(self, data_path: str = "doctors_db.json"):
        self.data_path = data_path
        self._doctors = []
        self._specializations = []
        self._load_data()

    def _load_data(self):
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._doctors = data.get('doctors', [])
                self._specializations = data.get('specializations', [])
        except FileNotFoundError:
            print(f"Error: {self.data_path} not found.")
            self._doctors = []
            self._specializations = []
        except json.JSONDecodeError:
            print(f"Error: Failed to decode {self.data_path}.")
            self._doctors = []
            self._specializations = []

    def get_all_doctors(self) -> List[Dict]:
        return self._doctors

    def get_doctor_by_id(self, doctor_id: int) -> Optional[Dict]:
        # Handle string/int conversion safely
        try:
            did = int(doctor_id)
        except (ValueError, TypeError):
            return None

        for doctor in self._doctors:
            if doctor.get('id') == did:
                return doctor
        return None

    def get_specializations(self) -> List[str]:
        return self._specializations
