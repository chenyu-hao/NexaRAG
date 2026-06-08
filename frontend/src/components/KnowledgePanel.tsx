import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, Database } from 'lucide-react';
import { uploadKnowledge } from '../lib/api';

const EXAMPLE_FILES = [
  'iphone16promax.txt',
  'huawei_mate70pro.txt',
  'xiaomi15pro.txt',
  'oppo_findx8pro.txt',
  'vivo_x200pro.txt',
];

interface Props {
  onUploaded: () => void;
}

export default function KnowledgePanel({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setResult(null);
    try {
      const res = await uploadKnowledge(file);
      setResult({ ok: true, msg: `${res.filename}: ${res.msg}` });
      onUploaded();
    } catch (e: any) {
      setResult({ ok: false, msg: e.message || '上传失败' });
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = '';
  };

  return (
    <main className="flex-1 overflow-y-auto bg-gray-50/60">
      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between gap-4 border-b border-gray-200 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Database size={17} className="text-brand-600" />
              <h2 className="text-base font-semibold text-gray-800">知识库管理</h2>
            </div>
            <p className="mt-1 text-xs text-gray-400">上传 TXT 文档后，知识库会同步刷新到聊天检索链路。</p>
          </div>

          <label className={`inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium cursor-pointer transition-colors
            ${uploading
              ? 'bg-gray-50 border-gray-200 text-gray-400'
              : 'bg-brand-700 text-white border-brand-700 hover:bg-brand-800'
            }`}>
            {uploading ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <Upload size={15} />
            )}
            {uploading ? '上传中...' : '上传 TXT 文件'}
            <input
              ref={fileRef}
              type="file"
              accept=".txt,text/plain"
              onChange={handleFileChange}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>

        <div className="mt-5 min-h-[28px]">
          {result && (
            <div className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md ${
              result.ok
                ? 'bg-green-50 text-green-700 border border-green-100'
                : 'bg-red-50 text-red-600 border border-red-100'
            }`}>
              {result.ok ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
              {result.msg}
            </div>
          )}
        </div>

        <section className="mt-5">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={14} className="text-gray-400" />
            <h3 className="text-xs font-semibold text-gray-600">知识库已有文档</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {EXAMPLE_FILES.map((f) => (
              <div key={f} className="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600">
                <FileText size={13} className="text-brand-500 shrink-0" />
                <span className="truncate font-mono">{f}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
