import '@testing-library/jest-dom';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CurriculumTable from '../src/components/student/CurriculumTable';

const course = (over: any) => ({
  course_code: 'AAA1001', course_name: '과목', credits: 3,
  course_type: '전공기초', year: 1, semester: 1, enrolled: false, ...over,
});

const data = (courses: any[]) => ({ '1학년': { '1학기': courses } });

describe('CurriculumTable 이수 상태', () => {
  // F는 이수 실패다. 예전에는 수강 이력만 보고 '이수완료 (F)'로 표시했다.
  it('F 학점은 이수완료가 아니라 이수 실패로 표시된다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, grade: 'F', completion_status: 'failed' }),
    ]) as any} />);
    expect(screen.getByText(/이수 실패/)).toBeInTheDocument();
    expect(screen.queryByText(/이수완료/)).not.toBeInTheDocument();
  });

  it('성적이 나온 과목은 이수완료로 표시된다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, grade: 'B', completion_status: 'completed' }),
    ]) as any} />);
    expect(screen.getByText(/이수완료/)).toBeInTheDocument();
  });

  it('성적이 없는 과목은 수강중으로 표시된다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, completion_status: 'in_progress' }),
    ]) as any} />);
    expect(screen.getByText('수강중')).toBeInTheDocument();
  });

  it('수강 이력이 없으면 미이수로 표시된다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ completion_status: 'not_taken' }),
    ]) as any} />);
    expect(screen.getByText('미이수')).toBeInTheDocument();
  });

  // completion_status가 없는 예전 응답에서도 F를 이수로 세면 안 된다.
  it('completion_status가 없어도 F는 이수완료가 아니다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, grade: 'F' }),
    ]) as any} />);
    expect(screen.queryByText(/이수완료/)).not.toBeInTheDocument();
  });
});

describe('CurriculumTable 비고', () => {
  // 비고는 '어디서 들었나'를 알려주는 칸이다. 같은 학과 과목에 '동등인정'을 띄우면
  // 이수현황 칸과 같은 말을 반복할 뿐이고, 성적을 보지 않아 F에도 붙었다.
  it('타 학과 개설 과목은 그 학과명을 보여준다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, grade: 'B', completion_status: 'completed',
               enrolled_department_name: '경영학부' }),
    ]) as any} />);
    expect(screen.getByText('경영학부')).toBeInTheDocument();
  });

  it('같은 학과 과목은 이수했어도 비고가 비어 있다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, grade: 'B', completion_status: 'completed' }),
    ]) as any} />);
    expect(screen.queryByText('동등인정')).not.toBeInTheDocument();
  });

  it('F 학점에 동등인정이 붙지 않는다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, grade: 'F', completion_status: 'failed' }),
    ]) as any} />);
    expect(screen.queryByText('동등인정')).not.toBeInTheDocument();
  });

  it('수강중에도 동등인정이 붙지 않는다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ enrolled: true, completion_status: 'in_progress' }),
    ]) as any} />);
    expect(screen.queryByText('동등인정')).not.toBeInTheDocument();
  });

  it('교양필수는 타 학과 개설이어도 비고를 비운다', () => {
    render(<CurriculumTable curriculumData={data([
      course({ course_type: '교양필수', enrolled: true, grade: 'B',
               completion_status: 'completed', enrolled_department_name: '경영학부' }),
    ]) as any} />);
    expect(screen.queryByText('경영학부')).not.toBeInTheDocument();
  });
});
