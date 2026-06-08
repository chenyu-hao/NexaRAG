import { useState } from 'react';
import { Archive, Minimize2 } from 'lucide-react';
import { compactContext, promoteDailyMemory } from '../lib/api';

interface Props {
  userId: string;
  sessionId: string | null;
}

type Status = {
  label: string;
  tone: 'idle' | 'success' | 'error';
};

function statusClass(tone: Status['tone']) {
  if (tone === 'success') return 'text-green-600 bg-green-50 border-green-100';
  if (tone === 'error') return 'text-red-600 bg-red-50 border-red-100';
  return 'text-gray-500 bg-gray-50 border-gray-100';
}

export default function MemoryControls({ userId, sessionId }: Props) {
  const [promoting, setPromoting] = useState(false);
  const [compacting, setCompacting] = useState(false);
  const [promoteStatus, setPromoteStatus] = useState<Status | null>(null);
  const [compactStatus, setCompactStatus] = useState<Status | null>(null);

  async function handlePromote() {
    setPromoting(true);
    setPromoteStatus(null);
    try {
      const result = await promoteDailyMemory({ user_id: userId, dry_run: false });
      const errors = result.errors.length ? ` · ${result.errors.length} 错误` : '';
      setPromoteStatus({
        label: `写入 ${result.promoted.length} 条，跳过 ${result.skipped.length} 条${errors}`,
        tone: result.errors.length ? 'error' : 'success',
      });
    } catch (error: any) {
      setPromoteStatus({ label: error.message || '写入失败', tone: 'error' });
    } finally {
      setPromoting(false);
    }
  }

  async function handleCompact() {
    if (!sessionId) return;
    setCompacting(true);
    setCompactStatus(null);
    try {
      const result = await compactContext({
        user_id: userId,
        session_id: sessionId,
        write_daily_snapshot: true,
      });
      const errors = result.errors.length ? ` · ${result.errors.length} 错误` : '';
      setCompactStatus({
        label: `${result.compact_context.length} 字 · ${result.placeholder_index.length} 占位${errors}`,
        tone: result.errors.length ? 'error' : 'success',
      });
    } catch (error: any) {
      setCompactStatus({ label: error.message || '压缩失败', tone: 'error' });
    } finally {
      setCompacting(false);
    }
  }

  return (
    <section>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-gray-400 mb-2 font-medium">
        <Archive size={10} />
        记忆工具
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={handlePromote}
          disabled={promoting}
          title="写入长期记忆"
          className="h-8 inline-flex items-center justify-center gap-1.5 rounded border border-gray-200 bg-white text-[11px] text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          <Archive size={13} />
          <span>{promoting ? '写入中' : '长期记忆'}</span>
        </button>
        <button
          type="button"
          onClick={handleCompact}
          disabled={compacting || !sessionId}
          title="压缩当前上下文"
          className="h-8 inline-flex items-center justify-center gap-1.5 rounded border border-gray-200 bg-white text-[11px] text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          <Minimize2 size={13} />
          <span>{compacting ? '压缩中' : '上下文'}</span>
        </button>
      </div>

      <div className="mt-2 space-y-1">
        {promoteStatus && (
          <div className={`rounded border px-2 py-1 text-[10px] ${statusClass(promoteStatus.tone)}`}>
            {promoteStatus.label}
          </div>
        )}
        {compactStatus && (
          <div className={`rounded border px-2 py-1 text-[10px] ${statusClass(compactStatus.tone)}`}>
            {compactStatus.label}
          </div>
        )}
      </div>
    </section>
  );
}
