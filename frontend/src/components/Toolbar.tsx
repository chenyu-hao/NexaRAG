import { Wrench, Circle, MessageSquare, Database } from 'lucide-react';
import type { HealthStatus } from '../types';

type PageKey = 'chat' | 'knowledge';

interface Props {
  health: HealthStatus | null;
  healthError: string;
  userId: string;
  activePage: PageKey;
  onPageChange: (page: PageKey) => void;
  onRefresh: () => void;
}

const NAV_ITEMS: Array<{ key: PageKey; label: string; Icon: typeof MessageSquare }> = [
  { key: 'chat', label: '聊天工作台', Icon: MessageSquare },
  { key: 'knowledge', label: '知识库管理', Icon: Database },
];

export default function Toolbar({
  health, healthError, userId, activePage, onPageChange, onRefresh,
}: Props) {
  const healthy = health?.status === 'healthy';

  return (
    <header className="flex items-center justify-between h-12 px-4 bg-white border-b border-gray-200 shrink-0 select-none">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-brand-700 flex items-center justify-center">
            <Wrench size={15} className="text-white" />
          </div>
          <span className="font-semibold text-sm tracking-tight text-gray-800">
            NexaRAG Console
          </span>
        </div>
        <span className="text-[10px] text-gray-300 px-1.5 py-0.5 bg-gray-100 rounded font-mono">
          v2.0
        </span>

        <nav className="flex items-center gap-0.5 rounded-md bg-gray-100 p-0.5">
          {NAV_ITEMS.map(({ key, label, Icon }) => {
            const active = activePage === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => onPageChange(key)}
                className={`inline-flex h-7 items-center gap-1.5 rounded px-2 text-xs font-medium transition-colors ${
                  active
                    ? 'bg-white text-brand-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon size={13} />
                <span>{label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        {/* 健康状态 */}
        <button
          onClick={onRefresh}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          title="刷新状态"
        >
          <Circle
            size={8}
            fill={healthError || !healthy ? '#ef4444' : '#22c55e'}
            stroke="none"
            className={!(healthError || !healthy) ? 'animate-pulse-dot' : ''}
          />
          <span>
            {healthError
              ? '异常'
              : healthy
                ? `正常 · ${health!.bm25_docs} 条知识 · ${health!.active_sessions} 会话`
                : '加载中...'}
          </span>
        </button>

        {/* 用户 ID */}
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <span className="text-gray-300">用户</span>
          <span className="font-mono text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded border border-gray-100">
            {userId || 'default'}
          </span>
        </div>
      </div>
    </header>
  );
}
