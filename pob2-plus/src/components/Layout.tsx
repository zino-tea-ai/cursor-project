import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-poe-bg flex flex-col">
      {/* 顶部导航栏 */}
      <header className="bg-poe-panel border-b border-poe-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-poe-gold">PoB2 Plus</h1>
            <span className="text-sm text-gray-500">Path of Exile 2 Build Planner</span>
          </div>
          <div className="flex items-center gap-4">
            <button className="btn-secondary text-sm">
              导入 Build
            </button>
            <button className="btn-primary text-sm">
              保存
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <main className="flex-1 flex">
        {children}
      </main>

      {/* 底部状态栏 */}
      <footer className="bg-poe-panel border-t border-poe-border px-4 py-2 text-sm text-gray-500">
        <div className="flex items-center justify-between">
          <span>PoB2 Plus v0.1.0 - 基于 Path of Building 2</span>
          <span>计算引擎: Lua (Fengari)</span>
        </div>
      </footer>
    </div>
  );
}



































