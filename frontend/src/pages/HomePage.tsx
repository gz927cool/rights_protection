export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="text-center max-w-2xl mx-auto px-4">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          劳动争议智能咨询系统
        </h1>
        <p className="text-gray-600 mb-8 text-lg">
          宿迁市总工会 · 九步引导式维权助手
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <div className="text-3xl mb-3">👨‍⚖️</div>
            <h3 className="font-semibold text-lg mb-2">律师视频咨询</h3>
            <p className="text-gray-500 text-sm">一对一视频咨询，专业律师在线解答</p>
            <p className="text-xs text-gray-400 mt-2">工作日 8:30-17:30</p>
          </div>
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <div className="text-3xl mb-3">🤖</div>
            <h3 className="font-semibold text-lg mb-2">AI智能问答</h3>
            <p className="text-gray-500 text-sm">九步引导，从咨询到文书一站式完成</p>
            <p className="text-xs text-gray-400 mt-2">随时可用</p>
          </div>
        </div>
        <a
          href="/chat"
          className="inline-flex items-center px-8 py-4 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition-colors text-lg shadow-sm"
        >
          开始AI咨询
        </a>
      </div>
    </div>
  )
}
