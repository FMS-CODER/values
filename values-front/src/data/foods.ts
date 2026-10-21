export const CATEGORIES = [
  '全部',
  '蔬菜',
  '水果',
  '谷物',
  '肉类',
  '蛋类',
  '豆制品',
  '奶制品',
  '坚果',
  '其他',
] as const

export type CategoryFilter = (typeof CATEGORIES)[number]
export type FoodCategory = Exclude<CategoryFilter, '全部'>

export interface FoodSource {
  /** 数据来源名称，例如 USDA SR Legacy */
  label: string
  /** 官方记录 ID；演示数据留空，避免与真实记录混淆 */
  recordId?: string
  url?: string
  /** 是否已对照官方来源核验数值 */
  verified: boolean
  /** 详情页展示的核验或使用说明 */
  note: string
}

export interface Food {
  id: number
  name: string
  category: FoodCategory
  image: string
  description: string
  /** 食品状态用于明确计量口径，例如「生，带皮」「熟」 */
  state: string
  source: FoodSource
  /** 该食物需要单独说明的营养声称提示，由数据层提供，页面不硬编码具体食物 */
  claimNote?: string
}

/** 分类标签配色，供卡片和详情页复用 */
export const CATEGORY_TONES: Record<FoodCategory, string> = {
  蔬菜: 'is-vegetable',
  水果: 'is-fruit',
  谷物: 'is-grain',
  肉类: 'is-meat',
  蛋类: 'is-egg',
  豆制品: 'is-soy',
  奶制品: 'is-dairy',
  坚果: 'is-nut',
  其他: 'is-other',
}

/** 未接入 USDA 校验的食物统一使用该来源标记，避免被误认为官方数据 */
const demoSource: FoodSource = {
  label: '界面演示数据',
  url: 'https://fdc.nal.usda.gov/',
  verified: false,
  note: '界面演示数据，待按食品状态与可靠营养数据库校验。',
}

/**
 * 食物基础信息表。
 * 营养素含量单独维护在 data/nutrients.ts，对应 food_nutrient 结构。
 */
export const foods: Food[] = [
  {
    id: 1,
    name: '西兰花',
    category: '蔬菜',
    image: '/foods/broccoli.jpg',
    description: '含有维生素 C、膳食纤维和多种矿物质，适合作为日常蔬菜选择。',
    state: '生，鲜品',
    source: demoSource,
  },
  {
    id: 2,
    name: '苹果',
    category: '水果',
    image: '/foods/apple.jpg',
    description: '含有膳食纤维和多种营养成分，适合作为日常水果选择。',
    state: '生，带皮',
    claimNote: '苹果含有维生素 C，但含量未达到「富含」的判定条件，因此不列为营养亮点，也不宜称其为「富含维生素 C」。',
    source: {
      label: 'USDA SR Legacy',
      recordId: '171688',
      url: 'https://fdc.nal.usda.gov/',
      verified: true,
      note: 'USDA SR Legacy 食品记录，FDC ID 171688。数值为示例引用，正式使用前请再次核对。',
    },
  },
  {
    id: 3,
    name: '胡萝卜',
    category: '蔬菜',
    image: '/foods/carrot.jpg',
    description: '富含 β-胡萝卜素，口感清甜，适合炒食、蒸煮或加入汤中。',
    state: '生，去皮',
    source: demoSource,
  },
  {
    id: 4,
    name: '鸡胸肉',
    category: '肉类',
    image: '/foods/chicken.jpg',
    description: '高蛋白、低脂肪的禽肉类食材，是日常补充优质蛋白的常见选择。',
    state: '生，去皮',
    source: demoSource,
  },
  {
    id: 5,
    name: '糙米',
    category: '谷物',
    image: '/foods/brown-rice.jpg',
    description: '保留麸皮和胚芽的全谷物，膳食纤维含量比精白米更丰富。',
    state: '熟',
    source: demoSource,
  },
  {
    id: 6,
    name: '鸡蛋',
    category: '蛋类',
    image: '/foods/egg.jpg',
    description: '优质蛋白与多种脂溶性营养素的来源，日常食用方便。',
    state: '生，全蛋',
    source: demoSource,
  },
  {
    id: 7,
    name: '豆腐',
    category: '豆制品',
    image: '/foods/tofu.jpg',
    description: '以大豆为原料的豆制品，提供植物蛋白和钙等营养成分。',
    state: '北豆腐',
    source: demoSource,
  },
  {
    id: 8,
    name: '牛奶',
    category: '奶制品',
    image: '/foods/milk.jpg',
    description: '提供蛋白质和钙，是日常奶制品中常见且方便的选择。',
    state: '全脂',
    source: demoSource,
  },
  {
    id: 9,
    name: '杏仁',
    category: '坚果',
    image: '/foods/almond.jpg',
    description: '富含脂肪和蛋白质的坚果，适合少量食用作为日常加餐。',
    state: '生，未烘焙',
    source: demoSource,
  },
  {
    id: 10,
    name: '红薯',
    category: '蔬菜',
    image: '/foods/sweet-potato.jpg',
    description: '含有膳食纤维和碳水化合物，蒸煮后口感绵软、香甜自然。',
    state: '生，带皮',
    source: demoSource,
  },
]
