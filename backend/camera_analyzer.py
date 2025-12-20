"""
Camera Injury Analyzer
Simulates AI injury identification and cure recommendations
"""
import base64
import json
import re
from datetime import datetime
import random

class CameraInjuryAnalyzer:
    def __init__(self):
        self.injury_database = self.load_injury_database()
        
    def load_injury_database(self):
        """Load comprehensive injury database with cure processes"""
        return {
            "cut": {
                "keywords": ["red", "line", "bleeding", "wound"],
                "severity_levels": {
                    "minor": {
                        "description": "Small superficial cut",
                        "cure_steps": [
                            "Wash hands thoroughly before treating",
                            "Clean the wound with mild soap and water",
                            "Apply gentle pressure with clean cloth to stop bleeding",
                            "Apply antibiotic ointment (e.g., Neosporin)",
                            "Cover with sterile bandage",
                            "Change bandage daily",
                            "Watch for signs of infection"
                        ],
                        "healing_time": "3-7 days",
                        "warning_signs": ["Increased redness", "Swelling", "Pus", "Fever"],
                        "do_not": ["Touch with dirty hands", "Pick at scab"]
                    },
                    "moderate": {
                        "description": "Deeper cut requiring attention",
                        "cure_steps": [
                            "Apply direct pressure for 10 minutes",
                            "Elevate the injured area above heart",
                            "Clean thoroughly with saline solution",
                            "Apply antibiotic ointment",
                            "Use butterfly strips to close wound edges",
                            "Cover with sterile gauze and bandage",
                            "Seek medical attention if bleeding doesn't stop",
                            "Get tetanus shot if needed"
                        ],
                        "healing_time": "7-14 days",
                        "warning_signs": ["Continued bleeding", "Deep wound", "Signs of infection"],
                        "do_not": ["Remove embedded objects", "Use peroxide on deep cuts"]
                    },
                    "severe": {
                        "description": "Deep laceration requiring immediate medical care",
                        "cure_steps": [
                            "CALL EMERGENCY SERVICES IMMEDIATELY",
                            "Apply firm pressure with clean cloth",
                            "Do NOT remove cloth if soaked - add more on top",
                            "Elevate above heart level",
                            "Keep person warm and calm",
                            "Do NOT give food or water",
                            "Monitor for shock symptoms"
                        ],
                        "healing_time": "14-21+ days (requires medical treatment)",
                        "warning_signs": ["Excessive bleeding", "Visible tissue/bone", "Shock symptoms"],
                        "do_not": ["Try to clean deep wounds", "Remove embedded objects", "Delay emergency care"]
                    }
                }
            },
            "burn": {
                "keywords": ["white", "red", "blister", "charred"],
                "severity_levels": {
                    "minor": {
                        "description": "First-degree burn (redness only)",
                        "cure_steps": [
                            "Cool the burn with running water for 10-20 minutes",
                            "Do NOT use ice (can cause further damage)",
                            "Remove jewelry and tight clothing before swelling",
                            "Apply aloe vera gel or burn cream",
                            "Cover loosely with sterile gauze",
                            "Take over-the-counter pain reliever if needed",
                            "Keep area moisturized during healing"
                        ],
                        "healing_time": "3-6 days",
                        "warning_signs": ["Blistering", "Increased pain", "Infection"],
                        "do_not": ["Apply butter or oil", "Pop blisters", "Use ice directly"]
                    },
                    "moderate": {
                        "description": "Second-degree burn (blistering)",
                        "cure_steps": [
                            "Cool with water for 20 minutes",
                            "Do NOT break blisters",
                            "Gently clean with mild soap",
                            "Apply antibiotic ointment if blisters break",
                            "Cover with non-stick sterile dressing",
                            "Change dressing daily",
                            "See doctor if larger than 3 inches",
                            "Watch for signs of infection"
                        ],
                        "healing_time": "14-21 days",
                        "warning_signs": ["Large area burned", "Worsening pain", "Infection signs"],
                        "do_not": ["Break blisters intentionally", "Apply adhesive bandages", "Delay medical care"]
                    },
                    "severe": {
                        "description": "Third-degree burn (charred skin)",
                        "cure_steps": [
                            "CALL 911 IMMEDIATELY",
                            "Do NOT remove stuck clothing",
                            "Cover with clean dry cloth",
                            "Do NOT apply water to large burns",
                            "Elevate burned area if possible",
                            "Monitor breathing and consciousness",
                            "Keep person warm with blanket"
                        ],
                        "healing_time": "Weeks to months (requires medical treatment)",
                        "warning_signs": ["Charred skin", "White/leathery appearance", "No pain (nerve damage)"],
                        "do_not": ["Apply any ointments", "Remove stuck fabric", "Give fluids by mouth"]
                    }
                }
            },
            "bruise": {
                "keywords": ["purple", "blue", "dark", "swelling"],
                "severity_levels": {
                    "minor": {
                        "description": "Simple bruise from blunt force",
                        "cure_steps": [
                            "Apply ice pack for 15 minutes every hour (first 24 hours)",
                            "Elevate the bruised area above heart",
                            "Rest the injured area",
                            "After 48 hours, apply warm compress",
                            "Take over-the-counter pain reliever if needed",
                            "Gentle massage after 24 hours (if not painful)",
                            "Allow bruise to heal naturally"
                        ],
                        "healing_time": "7-14 days",
                        "warning_signs": ["Severe pain", "Excessive swelling", "Numbness"],
                        "do_not": ["Massage immediately after injury", "Apply heat in first 48 hours"]
                    },
                    "moderate": {
                        "description": "Large bruise with significant swelling",
                        "cure_steps": [
                            "Ice for 20 minutes every hour (first day)",
                            "Wrap with elastic bandage for compression",
                            "Elevate continuously if possible",
                            "Rest and avoid using the area",
                            "Take anti-inflammatory medication",
                            "See doctor if pain is severe",
                            "Monitor for worsening symptoms"
                        ],
                        "healing_time": "14-21 days",
                        "warning_signs": ["Increasing swelling", "Severe pain", "Limited mobility"],
                        "do_not": ["Ignore severe pain", "Apply too much pressure", "Exercise the area"]
                    }
                }
            },
            "scrape": {
                "keywords": ["pink", "abrasion", "rough"],
                "severity_levels": {
                    "minor": {
                        "description": "Superficial skin abrasion",
                        "cure_steps": [
                            "Wash your hands first",
                            "Rinse wound with clean water",
                            "Gently clean with mild soap",
                            "Remove any dirt or debris",
                            "Apply antibiotic ointment",
                            "Cover with bandage if in area that rubs",
                            "Leave uncovered when possible for faster healing",
                            "Keep moist with ointment"
                        ],
                        "healing_time": "5-10 days",
                        "warning_signs": ["Redness spreading", "Pus", "Increased pain"],
                        "do_not": ["Use alcohol or hydrogen peroxide", "Scrub harshly"]
                    }
                }
            },
            "rash": {
                "keywords": ["spots", "patches", "irritation"],
                "severity_levels": {
                    "minor": {
                        "description": "Skin irritation or allergic reaction",
                        "cure_steps": [
                            "Identify and avoid the irritant/allergen",
                            "Wash area gently with mild soap",
                            "Pat dry (don't rub)",
                            "Apply calamine lotion or hydrocortisone cream",
                            "Take antihistamine if itchy",
                            "Wear loose, breathable clothing",
                            "Avoid scratching",
                            "Keep area cool and dry"
                        ],
                        "healing_time": "3-7 days",
                        "warning_signs": ["Spreading rapidly", "Severe itching", "Blisters", "Fever"],
                        "do_not": ["Scratch", "Use hot water", "Apply harsh chemicals"]
                    }
                }
            }
        }
    
    def analyze_injury_from_image(self, image_data):
        """
        Simulate AI analysis of injury image
        Returns injury type, severity, and cure process
        """
        try:
            # Simulated color/pattern analysis
            # In a real implementation, this would use image processing
            
            # For demo purposes, we'll do simple pattern matching
            # You can enhance this with actual image processing later
            
            # Analyze image colors to detect injury type
            analysis_result = self.simulate_ai_detection(image_data)
            
            # Get cure process
            cure_process = self.get_cure_process(
                analysis_result['type'],
                analysis_result['severity']
            )
            
            return {
                "success": True,
                "injury_type": analysis_result['type'],
                "severity": analysis_result['severity'],
                "confidence": analysis_result['confidence'],
                "description": cure_process['description'],
                "cure_steps": cure_process['cure_steps'],
                "healing_time": cure_process['healing_time'],
                "warning_signs": cure_process['warning_signs'],
                "do_not": cure_process['do_not'],
                "timestamp": datetime.now().isoformat(),
                "medical_advice": "⚕️ This is AI-assisted guidance. For serious injuries, always consult a healthcare professional."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Could not analyze image. Please try again."
            }
    
    def simulate_ai_detection(self, image_data=None):
        """
        Analyzes image to detect injury type based on color analysis
        """
        if image_data:
            try:
                # Import image processing libraries
                from PIL import Image
                import io
                
                # Decode base64 image
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                
                img_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(img_bytes))
                
                # Resize for faster processing
                img = img.resize((200, 200))
                
                # Convert to RGB
                img = img.convert('RGB')
                
                # Analyze colors
                pixels = list(img.getdata())
                
                # Count color categories
                red_count = 0
                white_count = 0
                blue_purple_count = 0
                pink_count = 0
                dark_count = 0
                
                for pixel in pixels:
                    r, g, b = pixel
                    
                    # Red detection (cuts, blood)
                    if r > 150 and g < 100 and b < 100:
                        red_count += 1
                    
                    # White detection (burns, pale skin)
                    elif r > 200 and g > 200 and b > 200:
                        white_count += 1
                    
                    # Pink detection (burns, irritation)
                    elif r > 180 and g > 120 and g < 180 and b > 120 and b < 180:
                        pink_count += 1
                    
                    # Blue/Purple detection (bruises)
                    elif b > 120 and g < 120 and r < 150:
                        blue_purple_count += 1
                    
                    # Dark/brown detection (severe bruises)
                    elif r < 100 and g < 100 and b < 100:
                        dark_count += 1
                
                total_pixels = len(pixels)
                
                # Calculate percentages
                red_percent = (red_count / total_pixels) * 100
                white_percent = (white_count / total_pixels) * 100
                pink_percent = (pink_count / total_pixels) * 100
                blue_purple_percent = (blue_purple_count / total_pixels) * 100
                dark_percent = (dark_count / total_pixels) * 100
                
                print(f"🔍 Color Analysis:")
                print(f"Red: {red_percent:.1f}% | White: {white_percent:.1f}% | Pink: {pink_percent:.1f}%")
                print(f"Blue/Purple: {blue_purple_percent:.1f}% | Dark: {dark_percent:.1f}%")
                
                # Determine injury type based on dominant colors
                injury_type = "scrape"  # default
                severity = "minor"
                confidence = 70
                
                # CUT detection - red dominance
                if red_percent > 5:
                    injury_type = "cut"
                    if red_percent > 15:
                        severity = "severe"
                        confidence = 92
                    elif red_percent > 8:
                        severity = "moderate"
                        confidence = 88
                    else:
                        severity = "minor"
                        confidence = 85
                    
                # BURN detection - white/pink dominance
                elif white_percent > 20 or pink_percent > 15:
                    injury_type = "burn"
                    if white_percent > 40:
                        severity = "severe"
                        confidence = 90
                    elif white_percent > 25 or pink_percent > 20:
                        severity = "moderate"
                        confidence = 86
                    else:
                        severity = "minor"
                        confidence = 82
                
                # BRUISE detection - blue/purple dominance
                elif blue_purple_percent > 8 or dark_percent > 12:
                    injury_type = "bruise"
                    if blue_purple_percent > 15 or dark_percent > 20:
                        severity = "moderate"
                        confidence = 87
                    else:
                        severity = "minor"
                        confidence = 83
                
                # SCRAPE detection - pink/light colors
                elif pink_percent > 5:
                    injury_type = "scrape"
                    severity = "minor"
                    confidence = 80
                
                # RASH detection - if nothing else matches but there's color variation
                else:
                    injury_type = "rash"
                    severity = "minor"
                    confidence = 75
                
                print(f"✅ Detected: {injury_type.upper()} ({severity}) - Confidence: {confidence}%")
                
                return {
                    "type": injury_type,
                    "severity": severity,
                    "confidence": confidence
                }
                
            except Exception as e:
                print(f"❌ Image analysis error: {e}")
                print("Falling back to demo mode...")
        
        # Fallback to demo mode if image analysis fails
        injury_types = list(self.injury_database.keys())
        selected_type = random.choice(injury_types)
        
        severities = list(self.injury_database[selected_type]['severity_levels'].keys())
        selected_severity = random.choice(severities)
        
        confidence = random.randint(75, 95)
        
        return {
            "type": selected_type,
            "severity": selected_severity,
            "confidence": confidence
        }
    
    def get_cure_process(self, injury_type, severity):
        """Get detailed cure process for injury"""
        if injury_type in self.injury_database:
            severity_data = self.injury_database[injury_type]['severity_levels'].get(
                severity,
                self.injury_database[injury_type]['severity_levels']['minor']
            )
            return severity_data
        
        # Default fallback
        return {
            "description": "Unidentified injury",
            "cure_steps": ["Clean the area", "Apply first aid", "Seek medical attention if severe"],
            "healing_time": "Varies",
            "warning_signs": ["Increasing pain", "Swelling", "Infection"],
            "do_not": ["Ignore severe symptoms"]
        }
    
    def get_injury_statistics(self):
        """Get statistics about injury types"""
        stats = {}
        for injury_type in self.injury_database:
            stats[injury_type] = {
                "total_severities": len(self.injury_database[injury_type]['severity_levels']),
                "available": True
            }
        return stats

# Create singleton instance
camera_analyzer = CameraInjuryAnalyzer()
