import { useEffect, useState } from 'react';
import { Layout, Sidebar, DamagePanel, PassiveTreeViewer, SkillPanel, EquipmentPanel } from './components';
import { useBuildStore } from './store/buildStore';
import { useI18nStore } from './store/i18nStore';
import { useBuildExportStore } from './store/buildExportStore';

type TabType = 'damage' | 'skills' | 'equipment' | 'tree';

function App() {
  const { initializeEngine } = useBuildStore();
  const { t, language, toggleLanguage } = useI18nStore();
  const { copyToClipboard, importFromClipboard } = useBuildExportStore();
  const [activeTab, setActiveTab] = useState<TabType>('skills');
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  useEffect(() => {
    initializeEngine();
  }, [initializeEngine]);

  const handleExport = async () => {
    const success = await copyToClipboard();
    setExportStatus(success ? t('build.exportSuccess') : 'Export failed');
    setTimeout(() => setExportStatus(null), 2000);
  };

  const handleImport = async () => {
    const success = await importFromClipboard();
    setExportStatus(success ? t('build.importSuccess') : t('build.importError'));
    setTimeout(() => setExportStatus(null), 2000);
  };

  const tabs: { id: TabType; labelKey: string }[] = [
    { id: 'skills', labelKey: 'nav.skills' },
    { id: 'equipment', labelKey: 'nav.equipment' },
    { id: 'damage', labelKey: 'nav.damage' },
    { id: 'tree', labelKey: 'nav.tree' },
  ];

  return (
    <Layout>
      <Sidebar />
      <div className="flex-1 flex flex-col">
        {/* 顶部工具栏 */}
        <div className="flex items-center justify-between px-4 py-2 bg-poe-panel border-b border-poe-border">
          {/* 标签页切换 */}
          <div className="flex">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-poe-gold border-b-2 border-poe-gold'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {t(tab.labelKey)}
              </button>
            ))}
          </div>
          
          {/* 右侧工具按钮 */}
          <div className="flex items-center gap-2">
            {/* 导入导出状态 */}
            {exportStatus && (
              <span className="text-sm text-green-400 mr-2">{exportStatus}</span>
            )}
            
            {/* 导入 Build */}
            <button
              onClick={handleImport}
              className="btn-secondary px-3 py-1.5 text-sm"
              title={t('build.import')}
            >
              {t('common.import')} Build
            </button>
            
            {/* 导出 Build */}
            <button
              onClick={handleExport}
              className="btn-primary px-3 py-1.5 text-sm"
              title={t('build.export')}
            >
              {t('common.export')}
            </button>
            
            {/* 语言切换 */}
            <button
              onClick={toggleLanguage}
              className="btn-secondary px-3 py-1.5 text-sm ml-2"
              title="Toggle Language"
            >
              {language === 'zh' ? 'EN' : '中'}
            </button>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'skills' && <SkillPanel />}
          {activeTab === 'equipment' && <EquipmentPanel />}
          {activeTab === 'damage' && <DamagePanel />}
          {activeTab === 'tree' && <PassiveTreeViewer />}
        </div>
      </div>
    </Layout>
  );
}

export default App;
