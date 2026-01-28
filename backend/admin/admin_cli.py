"""
관리자용 CLI 스크립트
데이터 업로드 및 진단 결과 관리를 위한 명령줄 도구
"""

import requests
import json
import argparse
import sys
from pathlib import Path
from typing import Optional, List
import time


class AdminCLI:
    """관리자 CLI 클래스"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.admin_url = f"{base_url}/api/admin"
    
    def upload_courses(self, file_path: str) -> dict:
        """과목 데이터 업로드"""
        print(f"📚 과목 데이터 업로드: {file_path}")
        
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.admin_url}/upload/courses/file",
                files={'file': f}
            )
        
        result = response.json()
        if result.get('success'):
            print(f"✅ 성공!")
            print(f"   - 새로 추가: {result['uploaded_count']}")
            print(f"   - 업데이트: {result['updated_count']}")
            if result.get('errors'):
                print(f"   ⚠️  오류: {len(result['errors'])}")
                for error in result['errors'][:5]:
                    print(f"      - {error}")
        else:
            print(f"❌ 실패: {result.get('message')}")
        
        return result
    
    def upload_students(self, file_path: str) -> dict:
        """학생 데이터 업로드"""
        print(f"👨‍🎓 학생 데이터 업로드: {file_path}")
        
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.admin_url}/upload/students/file",
                files={'file': f}
            )
        
        result = response.json()
        if result.get('success'):
            print(f"✅ 성공!")
            print(f"   - 새로 추가: {result['uploaded_count']}")
            print(f"   - 업데이트: {result['updated_count']}")
            if result.get('errors'):
                print(f"   ⚠️  오류: {len(result['errors'])}")
                for error in result['errors'][:5]:
                    print(f"      - {error}")
        else:
            print(f"❌ 실패: {result.get('message')}")
        
        return result
    
    def upload_enrollments(self, file_path: str) -> dict:
        """수강 데이터 업로드"""
        print(f"📝 수강 데이터 업로드: {file_path}")
        
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.admin_url}/upload/enrollments/file",
                files={'file': f}
            )
        
        result = response.json()
        if result.get('success'):
            print(f"✅ 성공!")
            print(f"   - 새로 추가: {result['uploaded_count']}")
            print(f"   - 업데이트: {result['updated_count']}")
            if result.get('errors'):
                print(f"   ⚠️  오류: {len(result['errors'])}")
                for error in result['errors'][:5]:
                    print(f"      - {error}")
        else:
            print(f"❌ 실패: {result.get('message')}")
        
        return result
    
    def bulk_evaluate(
        self,
        student_ids: Optional[List[str]] = None,
        department_ids: Optional[List[int]] = None,
        force_recalculate: bool = False
    ) -> dict:
        """대량 진단 실행"""
        print("🔍 대량 진단 실행 중...")
        
        payload = {"force_recalculate": force_recalculate}
        if student_ids:
            payload["student_ids"] = student_ids
        if department_ids:
            payload["department_ids"] = department_ids
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.admin_url}/evaluate/bulk",
                json=payload,
                timeout=600  # 10분 타임아웃
            )
            
            elapsed_time = time.time() - start_time
            result = response.json()
            
            if result.get('success'):
                print(f"✅ 진단 완료! (소요 시간: {elapsed_time:.2f}초)")
                print(f"   - 총 학생: {result['total_students']}")
                print(f"   - 총 학과: {result['total_departments']}")
                print(f"   - 총 진단: {result['total_evaluations']}")
                print(f"   - 성공: {result['success_count']}")
                print(f"   - 실패: {result['error_count']}")
                
                if result.get('errors'):
                    print(f"\n   ⚠️  오류 목록:")
                    for error in result['errors'][:10]:
                        print(f"      - {error}")
            else:
                print(f"❌ 진단 실패: {result.get('message')}")
            
            return result
        
        except requests.Timeout:
            print("❌ 타임아웃 오류: 진단 시간이 너무 오래 걸립니다.")
            print("   작은 배치로 나눠서 실행해보세요.")
            return {"success": False, "message": "Timeout"}
    
    def get_stats(self) -> dict:
        """진단 결과 통계 조회"""
        print("📊 진단 결과 통계 조회...")
        
        response = requests.get(f"{self.admin_url}/evaluate/stats")
        stats = response.json()
        
        print(f"\n=== 진단 결과 통계 ===")
        print(f"총 캐시된 진단: {stats['total_cached']}")
        if stats.get('last_update'):
            print(f"마지막 업데이트: {stats['last_update']}")
        
        if stats.get('cached_by_department'):
            print(f"\n학과별 캐시:")
            for dept, count in sorted(
                stats['cached_by_department'].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                print(f"  - {dept}: {count}")
        
        return stats
    
    def clear_cache(self, department_id: Optional[int] = None) -> dict:
        """캐시 삭제"""
        if department_id:
            print(f"🗑️  학과 ID {department_id}의 캐시 삭제 중...")
            response = requests.delete(
                f"{self.admin_url}/evaluate/cache",
                params={"department_id": department_id}
            )
        else:
            print("🗑️  전체 캐시 삭제 중...")
            response = requests.delete(f"{self.admin_url}/evaluate/cache")
        
        result = response.json()
        
        if result.get('success'):
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
        return result
    
    def upload_all(self, data_dir: str):
        """모든 데이터 일괄 업로드"""
        data_path = Path(data_dir)
        
        print(f"\n{'='*60}")
        print(f"📦 데이터 일괄 업로드 시작: {data_dir}")
        print(f"{'='*60}\n")
        
        # 1. 과목 데이터
        courses_file = data_path / "courses.json"
        if courses_file.exists():
            self.upload_courses(str(courses_file))
        else:
            print(f"⚠️  과목 데이터 파일 없음: {courses_file}")
        
        print()
        
        # 2. 학생 데이터
        students_file = data_path / "students.json"
        if students_file.exists():
            self.upload_students(str(students_file))
        else:
            print(f"⚠️  학생 데이터 파일 없음: {students_file}")
        
        print()
        
        # 3. 수강 데이터
        enrollments_file = data_path / "enrollments.json"
        if enrollments_file.exists():
            self.upload_enrollments(str(enrollments_file))
        else:
            print(f"⚠️  수강 데이터 파일 없음: {enrollments_file}")
        
        print(f"\n{'='*60}")
        print("✅ 데이터 업로드 완료!")
        print(f"{'='*60}\n")


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description="Lions Dashboard 관리자 CLI 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 과목 데이터 업로드
  python admin_cli.py upload-courses data/courses.json
  
  # 학생 데이터 업로드
  python admin_cli.py upload-students data/students.json
  
  # 수강 데이터 업로드
  python admin_cli.py upload-enrollments data/enrollments.json
  
  # 모든 데이터 일괄 업로드
  python admin_cli.py upload-all data/
  
  # 전체 진단 실행
  python admin_cli.py evaluate
  
  # 강제 재진단
  python admin_cli.py evaluate --force
  
  # 통계 조회
  python admin_cli.py stats
  
  # 캐시 삭제
  python admin_cli.py clear-cache
        """
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:8080',
        help='API 서버 URL (기본값: http://localhost:8080)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='명령어')
    
    # upload-courses
    parser_courses = subparsers.add_parser('upload-courses', help='과목 데이터 업로드')
    parser_courses.add_argument('file', help='과목 데이터 JSON 파일')
    
    # upload-students
    parser_students = subparsers.add_parser('upload-students', help='학생 데이터 업로드')
    parser_students.add_argument('file', help='학생 데이터 JSON 파일')
    
    # upload-enrollments
    parser_enrollments = subparsers.add_parser('upload-enrollments', help='수강 데이터 업로드')
    parser_enrollments.add_argument('file', help='수강 데이터 JSON 파일')
    
    # upload-all
    parser_all = subparsers.add_parser('upload-all', help='모든 데이터 일괄 업로드')
    parser_all.add_argument('directory', help='데이터 디렉토리')
    
    # evaluate
    parser_evaluate = subparsers.add_parser('evaluate', help='대량 진단 실행')
    parser_evaluate.add_argument('--force', action='store_true', help='강제 재진단')
    parser_evaluate.add_argument('--students', nargs='+', help='특정 학생 ID 목록')
    parser_evaluate.add_argument('--departments', type=int, nargs='+', help='특정 학과 ID 목록')
    
    # stats
    subparsers.add_parser('stats', help='진단 결과 통계 조회')
    
    # clear-cache
    parser_clear = subparsers.add_parser('clear-cache', help='캐시 삭제')
    parser_clear.add_argument('--department', type=int, help='특정 학과 ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # CLI 인스턴스 생성
    cli = AdminCLI(args.url)
    
    # 명령어 실행
    try:
        if args.command == 'upload-courses':
            cli.upload_courses(args.file)
        
        elif args.command == 'upload-students':
            cli.upload_students(args.file)
        
        elif args.command == 'upload-enrollments':
            cli.upload_enrollments(args.file)
        
        elif args.command == 'upload-all':
            cli.upload_all(args.directory)
        
        elif args.command == 'evaluate':
            cli.bulk_evaluate(
                student_ids=args.students,
                department_ids=args.departments,
                force_recalculate=args.force
            )
        
        elif args.command == 'stats':
            cli.get_stats()
        
        elif args.command == 'clear-cache':
            cli.clear_cache(args.department)
    
    except requests.ConnectionError:
        print(f"❌ 서버 연결 실패: {args.url}")
        print("   서버가 실행 중인지 확인해주세요.")
        sys.exit(1)
    
    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없습니다: {e}")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
