import { Cookie, Baby, Drumstick } from 'lucide-react'

interface FoodItemProps {
  name: string
  image: string
  protein: string
  carbs: string
  fat: string
  calories: number
}

function FoodItem({ name, image, protein, carbs, fat, calories }: FoodItemProps) {
  return (
    <div 
      className="flex items-center bg-surface rounded-2xl p-2.5 shadow-card"
      data-testid="food-item"
    >
      {/* 食物图片 */}
      <div 
        className="w-16 h-16 rounded-xl bg-gray-200 overflow-hidden flex-shrink-0"
        style={{
          backgroundImage: `url(${image})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        {/* 占位图 - 使用渐变背景 */}
        <div className="w-full h-full bg-gradient-to-br from-orange-200 to-orange-400" />
      </div>
      
      {/* 食物信息 */}
      <div className="flex-1 ml-4">
        <h3 className="text-base font-medium text-text-primary mb-1.5">{name}</h3>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <Cookie size={14} className="text-accent-blue" />
            <span className="text-sm text-text-secondary">{protein}</span>
          </div>
          <div className="flex items-center gap-1">
            <Baby size={14} className="text-accent-orange" />
            <span className="text-sm text-text-secondary">{carbs}</span>
          </div>
          <div className="flex items-center gap-1">
            <Drumstick size={14} className="text-accent-pink" />
            <span className="text-sm text-text-secondary">{fat}</span>
          </div>
        </div>
      </div>
      
      {/* 卡路里 */}
      <div className="text-right">
        <span className="text-xl font-semibold text-text-primary">{calories}</span>
        <p className="text-xs text-text-tertiary">Calories</p>
      </div>
    </div>
  )
}

export function FoodList() {
  const foods: FoodItemProps[] = [
    {
      name: "Hunter's Fried Chicken",
      image: '/food1.jpg',
      protein: '54g',
      carbs: '39g',
      fat: '60g',
      calories: 945,
    },
    {
      name: 'Salad',
      image: '/food2.jpg',
      protein: '54g',
      carbs: '39g',
      fat: '60g',
      calories: 300,
    },
    {
      name: "Hunter's Fried Chicken",
      image: '/food3.jpg',
      protein: '54g',
      carbs: '39g',
      fat: '60g',
      calories: 945,
    },
  ]

  return (
    <div className="space-y-3 mt-2" data-testid="food-list">
      {foods.map((food, index) => (
        <FoodItem key={index} {...food} />
      ))}
    </div>
  )
}
