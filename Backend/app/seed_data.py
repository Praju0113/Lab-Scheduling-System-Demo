from __future__ import annotations

from datetime import date, datetime, time, timezone

from app.catalog import build_test_catalog, catalog_item, test_catalog_map

DEFAULT_OPENING_TIME = time.fromisoformat('07:00:00')
DEFAULT_CLOSING_TIME = time.fromisoformat('23:30:00')

ECG_CATEGORY = 'Electrocardiogram (ECG)'
TMT_CATEGORY = 'Treadmill Test (TMT)'
ULTRASOUND_CATEGORY = 'Ultrasound Scan'
ECHO_CATEGORY = '2D Echocardiogram (2D Echo)'
MAMMOGRAPHY_CATEGORY = 'Mammography'
DEXA_CATEGORY = 'Dual-Energy X-ray Absorptiometry (DEXA) Scan'
XRAY_CATEGORY = 'X-Ray Imaging'
AUDIOMETRY_CATEGORY = 'Pure Tone Audiometry'
OPHTHALMOLOGY_CATEGORY = 'Ophthalmology Examination'
PAP_SMEAR_CATEGORY = 'Pap Smear Test'
URINE_CATEGORY = 'Urine Examination (Input Condition: Bladder needs to be full)'
STOOL_CATEGORY = 'Stool Examination'
BLOOD_CATEGORY = 'Blood Test (Includes all Pathology, Biochemistry, Hematology, Immunology, and Genetics)'

DEFAULT_SPECIALISTS = [
    {'name': 'Anand Sharma', 'gender': 'Male', 'shift_start': time.fromisoformat('08:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Priya Menon', 'gender': 'Female', 'shift_start': time.fromisoformat('08:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Ravi Gupta', 'gender': 'Male', 'shift_start': time.fromisoformat('09:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Meera Iyer', 'gender': 'Female', 'shift_start': time.fromisoformat('09:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Kiran Das', 'gender': 'Male', 'shift_start': time.fromisoformat('10:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Neha Rao', 'gender': 'Female', 'shift_start': time.fromisoformat('10:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Sanjay Pillai', 'gender': 'Male', 'shift_start': time.fromisoformat('08:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Asha Verma', 'gender': 'Female', 'shift_start': time.fromisoformat('08:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Deepak Nair', 'gender': 'Male', 'shift_start': time.fromisoformat('09:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Lakshmi Menon', 'gender': 'Female', 'shift_start': time.fromisoformat('09:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Arun Thomas', 'gender': 'Male', 'shift_start': time.fromisoformat('10:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Divya Kapoor', 'gender': 'Female', 'shift_start': time.fromisoformat('10:00'), 'shift_end': time.fromisoformat('23:00')},
    {'name': 'Nitin Rao', 'gender': 'Male', 'shift_start': time.fromisoformat('08:00'), 'shift_end': time.fromisoformat('23:00')},
]

DEFAULT_LABS = [
    {'name': 'ECG Lab 1', 'category': ECG_CATEGORY, 'floor': 'First Floor', 'room_number': 'F-101', 'specialist_index': 1, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 2, 'supported_test_codes': []},
    {'name': 'TMT Lab 1', 'category': TMT_CATEGORY, 'floor': 'First Floor', 'room_number': 'F-102', 'specialist_index': 2, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 5, 'supported_test_codes': []},
    {'name': 'Ultrasound Lab 1', 'category': ULTRASOUND_CATEGORY, 'floor': 'First Floor', 'room_number': 'F-103', 'specialist_index': 3, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 5, 'supported_test_codes': []},
    {'name': '2D Echo Lab 1', 'category': ECHO_CATEGORY, 'floor': 'First Floor', 'room_number': 'F-104', 'specialist_index': 4, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 5, 'supported_test_codes': []},
    {'name': 'Mammography Lab 1', 'category': MAMMOGRAPHY_CATEGORY, 'floor': 'Ground Floor', 'room_number': 'G-105', 'specialist_index': 6, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 5, 'supported_test_codes': []},
    {'name': 'DEXA Lab 1', 'category': DEXA_CATEGORY, 'floor': 'Ground Floor', 'room_number': 'G-106', 'specialist_index': 7, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 4, 'supported_test_codes': []},
    {'name': 'X-Ray Lab 1', 'category': XRAY_CATEGORY, 'floor': 'Ground Floor', 'room_number': 'G-107', 'specialist_index': 8, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 4, 'supported_test_codes': []},
    {'name': 'Audiometry Lab 1', 'category': AUDIOMETRY_CATEGORY, 'floor': 'First Floor', 'room_number': 'F-108', 'specialist_index': 9, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 3, 'supported_test_codes': []},
    {'name': 'Ophthalmology Lab 1', 'category': OPHTHALMOLOGY_CATEGORY, 'floor': 'First Floor', 'room_number': 'F-109', 'specialist_index': 10, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 3, 'supported_test_codes': []},
    {'name': 'Pap Smear Lab 1', 'category': PAP_SMEAR_CATEGORY, 'floor': 'Ground Floor', 'room_number': 'G-110', 'specialist_index': 12, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 4, 'supported_test_codes': []},
    {'name': 'Urine Lab 1', 'category': URINE_CATEGORY, 'floor': 'Ground Floor', 'room_number': 'G-111', 'specialist_index': 11, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 2, 'supported_test_codes': []},
    {'name': 'Stool Lab 1', 'category': STOOL_CATEGORY, 'floor': 'Ground Floor', 'room_number': 'G-112', 'specialist_index': 13, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 2, 'supported_test_codes': []},
    {'name': 'Blood Lab 1', 'category': BLOOD_CATEGORY, 'floor': 'Ground Floor', 'room_number': 'G-113', 'specialist_index': 5, 'is_active': True, 'opening_time': DEFAULT_OPENING_TIME, 'closing_time': DEFAULT_CLOSING_TIME, 'cleanup_duration_minutes': 2, 'supported_test_codes': []},
]

SEED_NAME_ALIASES = {'CBC': 'CBC / CBC with PS / CBCESR', 'LFT': 'Liver Function Test / Extended / Autoantibody', 'RFT': 'Renal Function Test', 'TSH': 'THYROID PROFILE / Thyroid Function Test / TSH', 'Fasting Blood Sugar': 'Glucose (Fasting, PP, Random, Challenge, Tolerance)', 'ECG': 'ECG', 'Ultrasound Scan': 'Ultrasound Scan', 'Urine Examination': 'Urine Examination', 'Ophthalmology Examination': 'Ophthalmology Examination', 'Audiometry-Test': 'Audiometry-Test'}

VISIT_TEMPLATES = [
    {'phr_reference_id': 'PHR-0001', 'patient_name': 'Aarav Sharma', 'patient_age': 61, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '08:05', 'patient_snapshot': {'phone': '9000011111'}, 'tests': [
        {'test_code': 'CBC', 'test_name': 'CBC', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'ULTRASOUND_SCAN', 'test_name': 'Ultrasound Scan', 'category': ULTRASOUND_CATEGORY, 'duration_minutes': 20, 'tags': ['FULL_BLADDER'], 'condition_category': 'Imaging (Full Bladder)'},
        {'test_code': 'URINE_EXAMINATION', 'test_name': 'Urine Examination', 'category': URINE_CATEGORY, 'duration_minutes': 10, 'tags': ['FULL_BLADDER'], 'condition_category': 'Urine - Spot (Full Bladder)'},
    ]},
    {'phr_reference_id': 'PHR-0002', 'patient_name': 'Diya Patel', 'patient_age': 34, 'patient_gender': 'Female', 'priority_type': 'EMERGENCY', 'arrival_clock': '08:12', 'patient_snapshot': {'phone': '9000022222'}, 'tests': [
        {'test_code': 'ELECTROCARDIOGRAM_ECG', 'test_name': 'ECG', 'category': ECG_CATEGORY, 'duration_minutes': 15, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0003', 'patient_name': 'Ira Nair', 'patient_age': 1, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '08:25', 'patient_snapshot': {'phone': '9000033333'}, 'tests': [
        {'test_code': 'OPHTHALMOLOGY_EXAMINATION', 'test_name': 'Ophthalmology Examination', 'category': OPHTHALMOLOGY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
        {'test_code': 'AUDIOMETRY_TEST', 'test_name': 'Audiometry-Test', 'category': AUDIOMETRY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0004', 'patient_name': 'Rohan Kumar', 'patient_age': 52, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '08:32', 'patient_snapshot': {'phone': '9000044444'}, 'tests': [
        {'test_code': 'FASTING_BLOOD_SUGAR', 'test_name': 'Fasting Blood Sugar', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Strict Fasting Blood'},
    ]},
    {'phr_reference_id': 'PHR-0005', 'patient_name': 'Nisha Varma', 'patient_age': 46, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '08:41', 'patient_snapshot': {'phone': '9000055555'}, 'tests': [
        {'test_code': 'LFT', 'test_name': 'LFT', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'AUDIOMETRY_TEST', 'test_name': 'Audiometry-Test', 'category': AUDIOMETRY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0006', 'patient_name': 'Karthik Iyer', 'patient_age': 29, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '08:55', 'patient_snapshot': {'phone': '9000066666'}, 'tests': [
        {'test_code': 'ULTRASOUND_SCAN', 'test_name': 'Ultrasound Scan', 'category': ULTRASOUND_CATEGORY, 'duration_minutes': 20, 'tags': ['FULL_BLADDER'], 'condition_category': 'Imaging (Full Bladder)'},
    ]},
    {'phr_reference_id': 'PHR-0007', 'patient_name': 'Sara Joseph', 'patient_age': 67, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '09:02', 'patient_snapshot': {'phone': '9000077777'}, 'tests': [
        {'test_code': 'OPHTHALMOLOGY_EXAMINATION', 'test_name': 'Ophthalmology Examination', 'category': OPHTHALMOLOGY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0008', 'patient_name': 'Arjun Mehta', 'patient_age': 38, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '09:10', 'patient_snapshot': {'phone': '9000088888'}, 'tests': [
        {'test_code': 'CBC', 'test_name': 'CBC', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'ELECTROCARDIOGRAM_ECG', 'test_name': 'ECG', 'category': ECG_CATEGORY, 'duration_minutes': 15, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0009', 'patient_name': 'Maya Reddy', 'patient_age': 58, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '09:18', 'patient_snapshot': {'phone': '9000099999'}, 'tests': [
        {'test_code': 'CBC', 'test_name': 'CBC', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'RFT', 'test_name': 'RFT', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'ULTRASOUND_SCAN', 'test_name': 'Ultrasound Scan', 'category': ULTRASOUND_CATEGORY, 'duration_minutes': 20, 'tags': ['FULL_BLADDER'], 'condition_category': 'Imaging (Full Bladder)'},
        {'test_code': 'URINE_EXAMINATION', 'test_name': 'Urine Examination', 'category': URINE_CATEGORY, 'duration_minutes': 10, 'tags': ['FULL_BLADDER'], 'condition_category': 'Urine - Spot (Full Bladder)'},
    ]},
    {'phr_reference_id': 'PHR-0010', 'patient_name': 'Vivaan Sethi', 'patient_age': 42, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '09:24', 'patient_snapshot': {'phone': '9000101010'}, 'tests': [
        {'test_code': 'TSH', 'test_name': 'TSH', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'OPHTHALMOLOGY_EXAMINATION', 'test_name': 'Ophthalmology Examination', 'category': OPHTHALMOLOGY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0011', 'patient_name': 'Anaya Bose', 'patient_age': 7, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '09:31', 'patient_snapshot': {'phone': '9000111111'}, 'tests': [
        {'test_code': 'AUDIOMETRY_TEST', 'test_name': 'Audiometry-Test', 'category': AUDIOMETRY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0012', 'patient_name': 'Rahul Bhat', 'patient_age': 63, 'patient_gender': 'Male', 'priority_type': 'EMERGENCY', 'arrival_clock': '09:36', 'patient_snapshot': {'phone': '9000121212'}, 'tests': [
        {'test_code': 'ELECTROCARDIOGRAM_ECG', 'test_name': 'ECG', 'category': ECG_CATEGORY, 'duration_minutes': 15, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
        {'test_code': 'CBC', 'test_name': 'CBC', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
    ]},
    {'phr_reference_id': 'PHR-0013', 'patient_name': 'Fatima Ali', 'patient_age': 49, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '09:44', 'patient_snapshot': {'phone': '9000131313'}, 'tests': [
        {'test_code': 'LFT', 'test_name': 'LFT', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'RFT', 'test_name': 'RFT', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
    ]},
    {'phr_reference_id': 'PHR-0014', 'patient_name': 'Kabir Arora', 'patient_age': 3, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '09:49', 'patient_snapshot': {'phone': '9000141414'}, 'tests': [
        {'test_code': 'OPHTHALMOLOGY_EXAMINATION', 'test_name': 'Ophthalmology Examination', 'category': OPHTHALMOLOGY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
        {'test_code': 'ULTRASOUND_SCAN', 'test_name': 'Ultrasound Scan', 'category': ULTRASOUND_CATEGORY, 'duration_minutes': 20, 'tags': ['FULL_BLADDER'], 'condition_category': 'Imaging (Full Bladder)'},
    ]},
    {'phr_reference_id': 'PHR-0015', 'patient_name': 'Pooja Sen', 'patient_age': 55, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '09:57', 'patient_snapshot': {'phone': '9000151515'}, 'tests': [
        {'test_code': 'FASTING_BLOOD_SUGAR', 'test_name': 'Fasting Blood Sugar', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Strict Fasting Blood'},
        {'test_code': 'TSH', 'test_name': 'TSH', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
    ]},
    {'phr_reference_id': 'PHR-0016', 'patient_name': 'Dev Malhotra', 'patient_age': 31, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '10:05', 'patient_snapshot': {'phone': '9000161616'}, 'tests': [
        {'test_code': 'ULTRASOUND_SCAN', 'test_name': 'Ultrasound Scan', 'category': ULTRASOUND_CATEGORY, 'duration_minutes': 20, 'tags': ['FULL_BLADDER'], 'condition_category': 'Imaging (Full Bladder)'},
        {'test_code': 'URINE_EXAMINATION', 'test_name': 'Urine Examination', 'category': URINE_CATEGORY, 'duration_minutes': 10, 'tags': ['FULL_BLADDER'], 'condition_category': 'Urine - Spot (Full Bladder)'},
    ]},
    {'phr_reference_id': 'PHR-0017', 'patient_name': 'Zoya Khan', 'patient_age': 26, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '10:12', 'patient_snapshot': {'phone': '9000171717'}, 'tests': [
        {'test_code': 'AUDIOMETRY_TEST', 'test_name': 'Audiometry-Test', 'category': AUDIOMETRY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
        {'test_code': 'OPHTHALMOLOGY_EXAMINATION', 'test_name': 'Ophthalmology Examination', 'category': OPHTHALMOLOGY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0018', 'patient_name': 'Harsh Vora', 'patient_age': 72, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '10:20', 'patient_snapshot': {'phone': '9000181818'}, 'tests': [
        {'test_code': 'CBC', 'test_name': 'CBC', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
        {'test_code': 'ELECTROCARDIOGRAM_ECG', 'test_name': 'ECG', 'category': ECG_CATEGORY, 'duration_minutes': 15, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
        {'test_code': 'OPHTHALMOLOGY_EXAMINATION', 'test_name': 'Ophthalmology Examination', 'category': OPHTHALMOLOGY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
    ]},
    {'phr_reference_id': 'PHR-0019', 'patient_name': 'Ishita Paul', 'patient_age': 44, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '10:28', 'patient_snapshot': {'phone': '9000191919'}, 'tests': [
        {'test_code': 'RFT', 'test_name': 'RFT', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
    ]},
    {'phr_reference_id': 'PHR-0020', 'patient_name': 'Yuvan Das', 'patient_age': 12, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '10:35', 'patient_snapshot': {'phone': '9000202020'}, 'tests': [
        {'test_code': 'AUDIOMETRY_TEST', 'test_name': 'Audiometry-Test', 'category': AUDIOMETRY_CATEGORY, 'duration_minutes': 20, 'tags': [], 'condition_category': 'Physical & Stress Tests'},
        {'test_code': 'CBC', 'test_name': 'CBC', 'category': BLOOD_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Standard Single-Draw Blood Tests'},
    ]},
    {'phr_reference_id': 'PHR-0021', 'patient_name': 'Naveen Pillai', 'patient_age': 37, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '10:42', 'patient_snapshot': {'phone': '9000212121'}, 'tests': [
        {'test_code': 'URINE_EXAMINATION', 'test_name': 'Urine Examination', 'category': URINE_CATEGORY, 'duration_minutes': 10, 'tags': [], 'condition_category': 'Urine - Spot'},
    ]},

    {'phr_reference_id': 'PHR-0022', 'patient_name': 'Mehul Jain', 'patient_age': 47, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '10:49', 'patient_snapshot': {'phone': '9000222222'}, 'tests': [
        {'test_name': 'TMT (Treadmill Test)'},
    ]},
    {'phr_reference_id': 'PHR-0023', 'patient_name': 'Sonia Kulkarni', 'patient_age': 39, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '10:56', 'patient_snapshot': {'phone': '9000232323'}, 'tests': [
        {'test_name': 'TMT (Treadmill Test)'},
    ]},
    {'phr_reference_id': 'PHR-0024', 'patient_name': 'Prakash Menon', 'patient_age': 51, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '11:03', 'patient_snapshot': {'phone': '9000242424'}, 'tests': [
        {'test_name': '2D Echocardiogram (2D Echo)'},
    ]},
    {'phr_reference_id': 'PHR-0025', 'patient_name': 'Rekha Suresh', 'patient_age': 62, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '11:10', 'patient_snapshot': {'phone': '9000252525'}, 'tests': [
        {'test_name': '2D Echocardiogram (2D Echo)'},
    ]},
    {'phr_reference_id': 'PHR-0026', 'patient_name': 'Anita George', 'patient_age': 45, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '11:17', 'patient_snapshot': {'phone': '9000262626'}, 'tests': [
        {'test_name': 'Mammography'},
    ]},
    {'phr_reference_id': 'PHR-0027', 'patient_name': 'Leena Thomas', 'patient_age': 53, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '11:24', 'patient_snapshot': {'phone': '9000272727'}, 'tests': [
        {'test_name': 'Mammography'},
    ]},
    {'phr_reference_id': 'PHR-0028', 'patient_name': 'Kala Mohan', 'patient_age': 60, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '11:31', 'patient_snapshot': {'phone': '9000282828'}, 'tests': [
        {'test_name': 'Dual-Energy X-ray Absorptiometry (DEXA) Scan'},
    ]},
    {'phr_reference_id': 'PHR-0029', 'patient_name': 'Ritesh Sharma', 'patient_age': 64, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '11:38', 'patient_snapshot': {'phone': '9000292929'}, 'tests': [
        {'test_name': 'Dual-Energy X-ray Absorptiometry (DEXA) Scan'},
    ]},
    {'phr_reference_id': 'PHR-0030', 'patient_name': 'Mahima Roy', 'patient_age': 36, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '11:45', 'patient_snapshot': {'phone': '9000303030'}, 'tests': [
        {'test_name': 'X-Ray Imaging'},
    ]},
    {'phr_reference_id': 'PHR-0031', 'patient_name': 'Kunal Bedi', 'patient_age': 41, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '11:52', 'patient_snapshot': {'phone': '9000313131'}, 'tests': [
        {'test_name': 'X-Ray Imaging'},
    ]},
    {'phr_reference_id': 'PHR-0032', 'patient_name': 'Deepa Nambiar', 'patient_age': 33, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '11:59', 'patient_snapshot': {'phone': '9000323232'}, 'tests': [
        {'test_name': 'GYNAEC. EXAM'},
    ]},
    {'phr_reference_id': 'PHR-0033', 'patient_name': 'Shweta Rao', 'patient_age': 48, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '12:06', 'patient_snapshot': {'phone': '9000333333'}, 'tests': [
        {'test_name': 'GYNAEC. EXAM'},
    ]},
    {'phr_reference_id': 'PHR-0034', 'patient_name': 'Nitin Khurana', 'patient_age': 43, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '12:13', 'patient_snapshot': {'phone': '9000343434'}, 'tests': [
        {'test_name': 'Stool Examination'},
    ]},
    {'phr_reference_id': 'PHR-0035', 'patient_name': 'Farah Siddiqui', 'patient_age': 29, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '12:20', 'patient_snapshot': {'phone': '9000353535'}, 'tests': [
        {'test_name': 'Stool Examination'},
    ]},
    {'phr_reference_id': 'PHR-0036', 'patient_name': 'Raghu Prasad', 'patient_age': 57, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '12:27', 'patient_snapshot': {'phone': '9000363636'}, 'tests': [
        {'test_name': 'TMT (Treadmill Test)'},
        {'test_name': '2D Echocardiogram (2D Echo)'},
    ]},
    {'phr_reference_id': 'PHR-0037', 'patient_name': 'Geetha Krishnan', 'patient_age': 58, 'patient_gender': 'Female', 'priority_type': 'NORMAL', 'arrival_clock': '12:34', 'patient_snapshot': {'phone': '9000373737'}, 'tests': [
        {'test_name': 'Mammography'},
        {'test_name': 'Dual-Energy X-ray Absorptiometry (DEXA) Scan'},
    ]},
    {'phr_reference_id': 'PHR-0038', 'patient_name': 'Bharat Singh', 'patient_age': 50, 'patient_gender': 'Male', 'priority_type': 'NORMAL', 'arrival_clock': '12:41', 'patient_snapshot': {'phone': '9000383838'}, 'tests': [
        {'test_name': 'X-Ray Imaging'},
        {'test_name': 'Stool Examination'},
    ]},
]


def _resolve_test(name: str) -> dict:
    canonical_name = SEED_NAME_ALIASES.get(name, name)
    return catalog_item(canonical_name)


def build_seed_visits(base_date: date | None = None) -> list[dict]:
    chosen_date = base_date or date.today()
    visits = []
    for row in VISIT_TEMPLATES:
        visit = dict(row)
        normalized_tests = []
        for test in row['tests']:
            canonical = _resolve_test(test['test_name'])
            normalized_tests.append({
                'test_code': canonical['test_code'],
                'test_name': canonical['test_name'],
                'category': canonical['category'],
                'duration_minutes': canonical['duration_minutes'],
                'tags': list(canonical.get('tags', [])),
                'condition_category': canonical.get('condition_category'),
            })
        visit['tests'] = normalized_tests
        hour, minute = map(int, row['arrival_clock'].split(':'))
        visit['arrival_time'] = datetime(chosen_date.year, chosen_date.month, chosen_date.day, hour, minute, tzinfo=timezone.utc).astimezone()
        visit.pop('arrival_clock', None)
        visits.append(visit)
    return visits




