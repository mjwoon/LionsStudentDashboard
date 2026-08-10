#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""group4 기반 mock 생성: 학생 300 + 수강 + 희망전공조사(2회차).
- 수강과목 = 확정지망(2차) 학과의 group4 1학년 커리큘럼 (상위학부 매핑 포함)
- 성적: 실제데이터 ~3.1 독립랜덤 / 수강량 프로파일 학기간 상관 / 선수과목 체인
- 1학기 완료(성적), 2학기 진행중(공란), 1학기 F는 진행중 2학기 재수강 불가
- 설문 2회차(100% 참여), 2차=확정지망=수강집중 대상
- group1 수정본 반영(102=자연,101=인문 / 디자인 800=계열,801주얼리,802융합,803영상 / 301 ICT)
"""
import csv, random, os
from collections import defaultdict
random.seed(42)

# 레포 루트 (scripts/ 상위). 어디서 실행해도 동작하도록 스크립트 위치 기준.
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N=300
SEM1=(2026,1); SEM2=(2026,2)

# ---------- group4 1학년 커리큘럼 로드 ----------
g4=defaultdict(list)
for r in csv.reader(open(f"{BASE}/group4_교육과정_전체.csv",encoding="utf-8-sig")):
    if r and r[0]!="학수번호" and r[4]=="1":
        code,name,cr,kind,yr,sem,teach,did=r
        g4[did].append((code,name,int(cr),kind,int(sem)))
for did in g4:                                   # 학과 내 학수번호 중복 제거(순서 유지)
    seen=set(); uniq=[]
    for c in g4[did]:
        if c[0] not in seen: seen.add(c[0]); uniq.append(c)
    g4[did]=uniq

# 커리큘럼 없는 학과 → 상위 학부 group4 커리큘럼 사용
CURRIC_SRC={"301":"303","304":"303","302":"300","401":"400","402":"400",
            "404":"403","405":"403","407":"406",
            "800":"800","801":"800","802":"800","803":"800"}
def curriculum(dept_id):
    src=CURRIC_SRC.get(str(dept_id),str(dept_id))
    return g4.get(src,[])

# 지망 학과 풀 (LIONS 100/101/102 제외), 트랙별
NAT=[200,201,202,203,204,205,206,207,208,209,210,
     300,301,302,303,304,306,307,400,401,402,403,404,405,406,407]
HUM=[500,501,502,600,601,602,603,700,800,801,802,803]

# ---------- 이름 / 성적 ----------
SURNAMES=["김","이","박","최","정","강","조","윤","장","임","한","오","서","신","권","황","안","송","류","전","홍","고","문","양","손","배","백","허"]
GIVEN=["민준","서준","도윤","예준","시우","하준","주원","지호","지후","준서","준우","현우","도현","건우","우진","선우","서진","연우","유준","정우","승현","시윤","서연","서윤","지우","서현","하은","하윤","민서","지유","윤서","채원","수아","지아","지윤","은서","다은","예은","수빈","소율","예린","시은","가은","유나","지민","다인","아인","하린","윤아","서아","시아","은채","혜원","나윤","가연"]
def kname(): return random.choice(SURNAMES)+random.choice(GIVEN)

GRADES=[("A+",4.5,417),("A",4.0,633),("B+",3.5,689),("B",3.0,730),("C+",2.5,463),("C",2.0,282),("D+",1.5,127),("D",1.0,103),("F",0.0,79)]
G_L=[g[0] for g in GRADES]; G_P={g[0]:g[1] for g in GRADES}; G_W=[g[2] for g in GRADES]
def pick_grade(): return random.choices(G_L,weights=G_W,k=1)[0]

def apply_profile(courses,profile):
    n=len(courses)
    if n==0: return []
    if profile=="minimal": k=min(n,random.randint(1,3))
    elif profile=="light": k=max(1,n-random.randint(1,2))
    else: k=n
    return [courses[i] for i in sorted(random.sample(range(n),k))]

def build_chains(s1,s2):
    """이름이 X1(1학기)/X2(2학기)인 과목쌍을 선수과목 체인으로 (예:일반물리학1→2, 미적분학1→2)."""
    s1by={nm[:-1]:code for code,nm,_,_,_ in s1 if nm.endswith("1")}
    ch={}
    for code,nm,_,_,_ in s2:
        if nm.endswith("2") and nm[:-1] in s1by: ch[code]=s1by[nm[:-1]]
    return ch

used=set()
def new_sid():
    while True:
        s=f"2026{random.randint(100000,999999)}"
        if s not in used: used.add(s); return s
def phone(): return f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}"

students=[]; enrollments=[]
for i in range(1,N+1):
    track=random.choice(["자연계열","인문사회계열"])
    pool=NAT if track=="자연계열" else HUM
    first,second=random.sample(pool,2)             # 확정(2차) 지망 = first
    department_id=(random.choices([102,100],[86,14])[0] if track=="자연계열"
                   else random.choices([101,100],[84,16])[0])   # group1 수정본: 102=자연,101=인문
    sid=new_sid()

    # ---- 희망전공조사 2회차 (학생 CSV 임베드) ----
    status1=random.choices([1,2,3],[50,35,15])[0]
    status2=max(status1,random.choices([1,2,3],[15,40,45])[0])
    scale1=random.choices([1,2,3,4,5],[22,26,24,16,12])[0]
    scale2=min(5,scale1+random.randint(0,2))
    if random.random()<0.30: fc1,sc1=second,first
    else: fc1,sc1=first,second
    base=dict(student_id=sid,name=kname(),email=f"student{i:03d}@hanyang.ac.kr",
              phone=phone(),department_id=department_id,pride="L",class_number=1,track=track)
    students.append({**base,"survey_round_id":1,"first_choice_id":fc1,"second_choice_id":sc1,
                     "decision_status_id":status1,"decision_scale":scale1})
    students.append({**base,"survey_round_id":2,"first_choice_id":first,"second_choice_id":second,
                     "decision_status_id":status2,"decision_scale":scale2})

    # ---- 수강: 확정지망(first) 커리큘럼 ----
    curr=curriculum(first)
    s1=[c for c in curr if c[4]==1]
    s2=[c for c in curr if c[4]==2]
    chains=build_chains(s1,s2)
    profile=random.choices(["full","light","minimal"],[0.76,0.18,0.06])[0]

    taken1=apply_profile(s1,profile)
    passed1=set()
    for code,name,cr,kind,_ in taken1:
        g=pick_grade()
        enrollments.append([sid,code,name,cr,kind,g,G_P[g],"false",SEM1[0],SEM1[1]])
        if g!="F": passed1.add(code)

    eligible2=[c for c in s2 if c[0] not in chains]
    eligible2+=[c for c in s2 if c[0] in chains and chains[c[0]] in passed1]
    order={c[0]:i for i,c in enumerate(s2)}
    eligible2.sort(key=lambda c:order[c[0]])
    taken2=apply_profile(eligible2,profile)
    for code,name,cr,kind,_ in taken2:
        enrollments.append([sid,code,name,cr,kind,"","","false",SEM2[0],SEM2[1]])
    # 1학기 F는 1학기 전용 → 진행중 2학기 재수강 없음

with open(f"{BASE}/sample_students_300.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(students[0].keys())); w.writeheader(); w.writerows(students)
with open(f"{BASE}/sample_enrollments_300.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["학번","학수번호","과목명","학점","이수구분","성적","평점","재수강여부","년도","학기"])
    w.writerows(enrollments)

print(f"학생 {len(set(s['student_id'] for s in students))}명 / 설문행 {len(students)} / 수강 {len(enrollments)}")
print(f"  1학기 {sum(1 for e in enrollments if e[9]==1)} / 2학기 {sum(1 for e in enrollments if e[9]==2)}")
