from database import SessionLocal
from models.database import DepartmentEntryRequirement, Department, RequirementCourse, Course

db = SessionLocal()

reqs = db.query(DepartmentEntryRequirement).all()
print(f'\n총 {len(reqs)}개 진입요건:\n')

for i, req in enumerate(reqs, 1):
    dept = db.query(Department).get(req.department_id)
    print(f'{i}. {dept.name} ({req.admission_year}년)')
    print(f'   - 요구: {req.target_grade_level} 이상 {req.required_count}과목 (logic_operator={req.logic_operator})')
    print(f'   - 설명: {req.requirement_text}')
    
    courses = db.query(RequirementCourse).filter(RequirementCourse.requirement_id == req.id).all()
    course_names = []
    for c in courses:
        course = db.query(Course).filter(Course.course_code == c.course_code).first()
        if course:
            course_names.append(f"{course.course_name} ({c.course_code})")
        else:
            course_names.append(c.course_code)
    
    print(f'   - 과목 ({len(courses)}개): {", ".join(course_names)}')
    print()

db.close()
