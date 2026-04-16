export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center relative overflow-hidden">
      {/* Background pattern: subtle dot grid */}
      <div
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage: 'radial-gradient(circle, #94a3b8 1px, transparent 1px)',
          backgroundSize: '28px 28px',
        }}
      />
      {/* Bottom-right decorative blob */}
      <div
        className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full opacity-20 blur-3xl pointer-events-none"
        style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
      />
      {/* Top-left decorative blob */}
      <div
        className="absolute -top-24 -left-24 w-80 h-80 rounded-full opacity-20 blur-3xl pointer-events-none"
        style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}
      />

      <div className="relative z-10 text-center max-w-2xl mx-auto px-6 py-16">
        {/* Eyebrow label */}
        <div className="animate-[fadeInDown_0.6s_ease-out_both] mb-6">
          <span className="inline-block px-4 py-1.5 bg-indigo-50 border border-indigo-100 rounded-full text-indigo-600 text-sm font-medium tracking-wide">
            宿迁市总工会 · 官方平台
          </span>
        </div>

        {/* Hero headline */}
        <h1 className="text-5xl sm:text-6xl font-bold text-slate-800 leading-tight mb-4 animate-[fadeInUp_0.6s_ease-out_0.15s_both]">
          劳动争议
          <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-blue-500">
            智能咨询系统
          </span>
        </h1>

        {/* Subheading */}
        <p className="text-slate-500 text-lg sm:text-xl mb-12 animate-[fadeInUp_0.6s_ease-out_0.3s_both]">
          九步引导式维权助手，让劳动者维权更简单
        </p>

        {/* Service cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 animate-[fadeInUp_0.6s_ease-out_0.45s_both]">
          {/* Card 1 - 律师视频咨询（暂不可用） */}
          <div className="group bg-white rounded-2xl p-7 border border-slate-100 shadow-sm transition-all duration-300 text-left cursor-not-allowed opacity-70">
            <div className="flex items-start justify-between mb-5">
              <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center text-2xl shadow-sm">
                👨‍⚖️
              </div>
              <div className="w-2 h-2 rounded-full bg-slate-200 mt-1" />
            </div>
            <h3 className="font-semibold text-slate-800 text-lg mb-2">律师视频咨询</h3>
            <p className="text-slate-400 text-sm leading-relaxed mb-4">
              一对一视频咨询，专业律师在线解答劳动权益问题
            </p>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
              <p className="text-xs text-slate-400">工作日 8:30 - 17:30</p>
            </div>
          </div>

          {/* Card 2 - AI智能问答 - 直接可点击跳转 */}
          <a
            href="/chat"
            className="group block bg-white rounded-2xl p-7 border border-slate-100 shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-blue-200 transition-all duration-300 text-left cursor-pointer"
          >
            <div className="flex items-start justify-between mb-5">
              <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center text-2xl shadow-sm group-hover:scale-110 transition-transform duration-300">
                🤖
              </div>
              <div className="w-2 h-2 rounded-full bg-slate-200 group-hover:bg-blue-400 transition-colors duration-300 mt-1" />
            </div>
            <h3 className="font-semibold text-slate-800 text-lg mb-2">AI智能问答</h3>
            <p className="text-slate-400 text-sm leading-relaxed mb-4">
              九步引导，从咨询到文书一站式完成，随时可用
            </p>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
              <p className="text-xs text-slate-400">24 小时随时可用</p>
            </div>
          </a>
        </div>

        {/* Trust badges */}
        <div className="animate-[fadeInUp_0.6s_ease-out_0.6s_both] mt-8 flex items-center justify-center gap-6 text-slate-400 text-sm">
          <span>快速响应</span>
          <span className="text-slate-300">·</span>
          <span>完全免费</span>
          <span className="text-slate-300">·</span>
          <span>保护隐私</span>
        </div>
      </div>

      {/* Keyframe definitions */}
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
