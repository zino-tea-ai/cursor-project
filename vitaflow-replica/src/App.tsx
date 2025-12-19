import { StatusBar } from './components/StatusBar'
import { Header } from './components/Header'
import { CalendarStrip } from './components/CalendarStrip'
import { CalorieCard } from './components/CalorieCard'
import { MacroCards } from './components/MacroCards'
import { MealTabs } from './components/MealTabs'
import { FoodList } from './components/FoodList'
import { BottomNavigation } from './components/BottomNavigation'

function App() {
  return (
    <div 
      className="relative bg-surface-background overflow-hidden shadow-xl rounded-[40px]"
      style={{ 
        width: 'var(--device-width)', 
        height: 'var(--device-height)' 
      }}
      data-testid="app-container"
    >
      {/* 状态栏 */}
      <StatusBar />
      
      {/* 主内容区 */}
      <div className="px-5 pb-[120px]">
        {/* 头部 */}
        <Header />
        
        {/* 日历条 */}
        <CalendarStrip />
        
        {/* 主内容容器 */}
        <div className="mt-5 space-y-4">
          {/* 卡路里摘要卡片 */}
          <CalorieCard />
          
          {/* 宏量营养素卡片 */}
          <MacroCards />
          
          {/* 餐食标签页 */}
          <MealTabs />
          
          {/* 食物列表 */}
          <FoodList />
        </div>
      </div>
      
      {/* 底部导航 */}
      <BottomNavigation />
    </div>
  )
}

export default App
