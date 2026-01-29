export default function Loading() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        {/* Logo */}
        <div className="w-12 h-12 bg-gradient-to-br from-primary-400 to-accent-500 rounded-xl flex items-center justify-center animate-pulse">
          <span className="text-white font-bold text-2xl">F</span>
        </div>
        
        {/* Spinner */}
        <div className="w-8 h-8 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
        
        {/* Loading Text */}
        <p className="text-slate-400 text-sm">加载中...</p>
      </div>
    </div>
  );
}
