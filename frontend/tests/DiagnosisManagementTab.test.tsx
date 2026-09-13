import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DiagnosisManagementTab from '../src/components/DiagnosisManagementTab';
import { api } from '../src/api';

vi.mock('../src/api', () => ({
  api: { admin: { bulkEvaluate: vi.fn(), getJobStatus: vi.fn() } },
}));

const RUNNING = {
  job_id: 'job-abc', status: 'PROGRESS',
  progress: { current: 40, total: 100, percent: 40, status: '진행 중' },
};

describe('DiagnosisManagementTab — 창을 나갔다 와도 진행이 이어진다', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    (api.admin.bulkEvaluate as any).mockResolvedValue({ job_id: 'job-abc', status: 'QUEUED' });
    (api.admin.getJobStatus as any).mockResolvedValue(RUNNING);
  });

  it('진단을 시작하면 job_id를 남겨 둔다', async () => {
    render(<DiagnosisManagementTab />);
    await userEvent.click(screen.getByRole('button', { name: /진단/ }));
    await waitFor(() => {
      expect(localStorage.getItem('diagnosis_job_id')).toBe('job-abc');
    });
  });

  // 탭을 벗어나면 컴포넌트가 언마운트되고 state가 사라진다. 서버 작업은 계속
  // 돌고 있으므로, 다시 들어왔을 때 진행 상황을 되찾을 수 있어야 한다.
  it('남아 있는 job_id가 있으면 다시 들어왔을 때 폴링을 재개한다', async () => {
    localStorage.setItem('diagnosis_job_id', 'job-abc');
    render(<DiagnosisManagementTab />);
    await waitFor(() => {
      expect(api.admin.getJobStatus).toHaveBeenCalledWith('job-abc');
    });
    expect(await screen.findByText('40%')).toBeInTheDocument();
  });

  it('작업이 끝나면 job_id를 지운다', async () => {
    (api.admin.getJobStatus as any).mockResolvedValue({
      job_id: 'job-abc', status: 'SUCCESS', result: { total: 1, success: 1, failed: 0 },
    });
    localStorage.setItem('diagnosis_job_id', 'job-abc');
    render(<DiagnosisManagementTab />);
    await waitFor(() => {
      expect(localStorage.getItem('diagnosis_job_id')).toBeNull();
    });
  });

  it('작업이 실패하면 job_id를 지운다', async () => {
    (api.admin.getJobStatus as any).mockResolvedValue({
      job_id: 'job-abc', status: 'FAILURE', error: '실패',
    });
    localStorage.setItem('diagnosis_job_id', 'job-abc');
    render(<DiagnosisManagementTab />);
    await waitFor(() => {
      expect(localStorage.getItem('diagnosis_job_id')).toBeNull();
    });
  });

  it('남은 job_id가 없으면 조회하지 않는다', async () => {
    render(<DiagnosisManagementTab />);
    await waitFor(() => expect(screen.getByRole('button', { name: /진단/ })).toBeEnabled());
    expect(api.admin.getJobStatus).not.toHaveBeenCalled();
  });
});
