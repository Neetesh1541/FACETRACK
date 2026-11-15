
from datetime import datetime, time, timedelta


DEFAULT_SHIFT_START = time(9, 0)
DEFAULT_GRACE_MINUTES = 15


def calculate_attendance_status(
    check_in_time,
    shift_start=None,
    grace_minutes=None
):
    if shift_start is None:
        shift_start = DEFAULT_SHIFT_START

    if grace_minutes is None:
        grace_minutes = DEFAULT_GRACE_MINUTES

    # Preserve timezone information
    shift_datetime = datetime.combine(
        check_in_time.date(),
        shift_start,
        tzinfo=check_in_time.tzinfo
    )

    late_after = shift_datetime + timedelta(
        minutes=grace_minutes
    )

    if check_in_time <= late_after:
        return "Present"

    return "Late"


def calculate_working_minutes(check_in, check_out):
    if check_out < check_in:
        raise ValueError(
            "Check-out cannot be earlier than check-in"
        )

    duration = check_out - check_in

    return int(duration.total_seconds() // 60)


def process_attendance_action(
    attendance_record,
    current_time
):
    if attendance_record is None:
        status = calculate_attendance_status(
            current_time
        )

        return {
            "action": "check_in",
            "status": status,
            "check_in": current_time,
            "check_out": None,
            "message": f"Check-in successful. Status: {status}"
        }

    if attendance_record.check_out is None:
        working_minutes = calculate_working_minutes(
            attendance_record.check_in,
            current_time
        )

        return {
            "action": "check_out",
            "status": attendance_record.status,
            "check_in": attendance_record.check_in,
            "check_out": current_time,
            "total_working_minutes": working_minutes,
            "message": "Check-out successful"
        }

    return {
        "action": "blocked",
        "message": "Attendance already completed for today"
    }
