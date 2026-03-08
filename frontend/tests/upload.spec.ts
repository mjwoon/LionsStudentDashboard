import { test, expect } from '@playwright/test';

test.describe('Admin Data Upload Tab', () => {
  test.beforeEach(async ({ page }) => {
    // 1. /admin 페이지 접속
    await page.goto('/admin');
    
    // 2. 글로벌 및 관리자 인증 우회 (Storage 설정)
    await page.evaluate(() => {
      localStorage.setItem('isAuthenticated', 'true');
      sessionStorage.setItem('admin_authenticated', 'true');
    });
    await page.reload();
    
    // 3. "데이터 업로드" 탭이 선택되어 있는지 확인
    await expect(page.locator('button:has-text("데이터 업로드")')).toHaveClass(/border-b-2/);
  });

  test('Mocking된 API로 파일 업로드 성공 시나리오 검증', async ({ page }) => {
    // 4. API 모킹 설정 (학생 + 희망전공조사 업로드 API)
    await page.route('**/api/admin/upload-grouped/students', async (route) => {
      // 업로드 요청을 가로채고 성공 응답 반환
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: '학생 및 희망전공조사 데이터가 성공적으로 업로드되었습니다.',
          uploaded_count: 10,
          updated_count: 5,
          sub_results: [
            { label: '학생 프로필 (2025학번 및 재학생)', success: true, uploaded_count: 10, updated_count: 5 },
            { label: '희망전공조사 결과', success: true, uploaded_count: 10, updated_count: 0 }
          ],
          errors: [],
          detailed_errors: []
        }),
      });
    });

    // 5. "학생 + 희망전공조사" 카드 내 파일 업로드 액션 
    // DataUploadTab에는 5가지 카드가 있으므로 제목으로 먼저 컨테이너를 찾습니다.
    const studentCard = page.locator('.bg-white', { hasText: '학생 + 희망전공조사' });
    
    // 파일 선택 (가짜 CSV 파일 생성 후 첨부)
    const fileChooserPromise = page.waitForEvent('filechooser');
    // "파일 선택" 라벨 클릭 (input[type=file]를 감싸고 있음)
    await studentCard.locator('label:has-text("파일 선택")').click();
    const fileChooser = await fileChooserPromise;
    
    await fileChooser.setFiles({
      name: 'mock_students.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('student_id,name\n20250001,테스터')
    });

    // 6. 업로드 버튼 클릭
    await studentCard.locator('button:has-text("업로드")').click();

    // 7. 모킹된 응답을 바탕으로 UI가 잘 업데이트 되었는지 확인 (성공 배지 및 카운트 검증)
    const resultBox = studentCard.locator('.bg-green-50.border-green-200');
    await expect(resultBox).toBeVisible();
    
    await expect(resultBox.locator('p.text-green-800')).toHaveText('학생 및 희망전공조사 데이터가 성공적으로 업로드되었습니다.');
    await expect(resultBox).toContainText('학생 프로필');
    await expect(resultBox).toContainText('희망전공조사 결과');
    await expect(resultBox).toContainText('총 새로 추가: 10개');
    await expect(resultBox).toContainText('총 업데이트: 5개');
  });
});
