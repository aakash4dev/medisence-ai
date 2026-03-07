from flask import Blueprint, request, jsonify
from services.appointment_service import AppointmentService
from repositories.doctor_repository import DoctorRepository

appointments_bp = Blueprint('appointments', __name__)
appointment_service = AppointmentService()
doctor_repository = DoctorRepository()

@appointments_bp.route('/doctors', methods=['GET'])
def get_doctors():
    """Get all doctors"""
    doctors = doctor_repository.get_all_doctors()
    # Match legacy format: {"success": True, "data": [...]}
    return jsonify({"success": True, "data": doctors}), 200

@appointments_bp.route('/specializations', methods=['GET'])
def get_specializations():
    """Get all specializations"""
    specializations = doctor_repository.get_specializations()
    return jsonify({"success": True, "data": specializations}), 200

@appointments_bp.route('/appointments/slots', methods=['GET'])
def get_slots():
    """Get available slots for a doctor on a date"""
    # Frontend sends 'doctor' but service expects 'doctor_id'
    doctor_id = request.args.get('doctor') or request.args.get('doctor_id')
    date = request.args.get('date')

    if not doctor_id or not date:
        return jsonify({"error": "doctor (id) and date are required"}), 400

    slots = appointment_service.get_available_slots(doctor_id, date)
    return jsonify({"success": True, "slots": slots}), 200

@appointments_bp.route('/appointments/book', methods=['POST'])
def create_appointment():
    """Create a new appointment"""
    data = request.json

    # Map frontend keys to backend keys if necessary
    # Frontend: userId, doctorId. Service: user_id, doctor_id
    if 'userId' in data:
        data['user_id'] = data['userId']
    if 'doctorId' in data:
        data['doctor_id'] = data['doctorId']

    result, status_code = appointment_service.create_booking(data)
    return jsonify(result), status_code

@appointments_bp.route('/appointments', methods=['GET'])
def get_appointments():
    """Get appointments for a user (query param style)"""
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    appointments = appointment_service.get_user_appointments(user_id)

    # Add combined ISO datetime for frontend formatting
    for apt in appointments:
        if 'date' in apt and 'time' in apt:
            # Combine YYYY-MM-DD and HH:MM to YYYY-MM-DDTHH:MM:00
            apt['datetime'] = f"{apt['date']}T{apt['time']}:00"

    return jsonify({"success": True, "data": appointments}), 200

@appointments_bp.route('/appointments/<user_id>', methods=['GET'])
def get_user_appointments_legacy(user_id):
    """Get appointments for a user (path param style)"""
    appointments = appointment_service.get_user_appointments(user_id)
    for apt in appointments:
        if 'date' in apt and 'time' in apt:
            apt['datetime'] = f"{apt['date']}T{apt['time']}:00"
    return jsonify({"success": True, "data": appointments}), 200

@appointments_bp.route('/appointments/<appointment_id>/cancel', methods=['POST', 'PUT', 'DELETE'])
@appointments_bp.route('/appointments/<appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    """Cancel an appointment"""
    # Be flexible: check query params first, then JSON body
    user_id = request.args.get('user_id') or request.args.get('userId')

    if not user_id and request.is_json:
        data = request.json or {}
        user_id = data.get('userId') or data.get('user_id')

    if not user_id:
        return jsonify({"success": False, "message": "User ID required"}), 400

    result, status_code = appointment_service.cancel_appointment(appointment_id, user_id)
    return jsonify(result), status_code

@appointments_bp.route('/appointments/<appointment_id>/reschedule', methods=['PUT'])
def reschedule_appointment(appointment_id):
    """Reschedule an appointment"""
    data = request.json or {}
    user_id = data.get('userId')
    new_date = data.get('date')
    new_time = data.get('time')

    if not user_id or not new_date or not new_time:
         return jsonify({"success": False, "message": "User ID, date, and time required"}), 400

    result, status_code = appointment_service.reschedule_appointment(appointment_id, user_id, new_date, new_time)
    return jsonify(result), status_code
