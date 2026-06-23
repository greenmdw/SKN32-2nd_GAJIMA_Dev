/**
 * Product data types and sample cosmetics data
 * Based on REES46 cosmetics dataset
 */

export interface Product {
  productId: string;
  sku: string;
  name: string;
  categoryId: string;
  category: string;
  brand: string;
  price: number;
  description?: string;
  image?: string;
}

// Sample cosmetics data from REES46 dataset
export const SAMPLE_PRODUCTS: Product[] = [
  {
    productId: 'sku_10001',
    sku: 'ADIDAS-FACE-CREAM-001',
    name: 'Adidas Face Cream Premium',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'adidas',
    price: 45000,
    description: 'Premium face cream with moisturizing formula',
  },
  {
    productId: 'sku_10002',
    sku: 'ADIDAS-SERUM-001',
    name: 'Adidas Vitamin C Serum',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'adidas',
    price: 52000,
    description: 'Brightening serum with vitamin C',
  },
  {
    productId: 'sku_10003',
    sku: 'LOREAL-FOUNDATION-001',
    name: 'L\'Oreal True Match Foundation',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'loreal',
    price: 38000,
    description: 'Full coverage foundation for all skin types',
  },
  {
    productId: 'sku_10004',
    sku: 'LOREAL-LIPSTICK-001',
    name: 'L\'Oreal Color Riche Lipstick',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'loreal',
    price: 28000,
    description: 'Long-lasting lipstick in vibrant colors',
  },
  {
    productId: 'sku_10005',
    sku: 'MAYBELLINE-MASCARA-001',
    name: 'Maybelline Lash Sensational Mascara',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'maybelline',
    price: 18000,
    description: 'Volumizing mascara for dramatic lashes',
  },
  {
    productId: 'sku_10006',
    sku: 'NEUTROGENA-SUNSCREEN-001',
    name: 'Neutrogena Ultra Sheer Sunscreen SPF 50',
    categoryId: 'cat_03',
    category: 'Sun Care',
    brand: 'neutrogena',
    price: 22000,
    description: 'Lightweight sunscreen with SPF 50 protection',
  },
  {
    productId: 'sku_10007',
    sku: 'CLINIQUE-CLEANSER-001',
    name: 'Clinique Liquid Facial Soap',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'clinique',
    price: 35000,
    description: 'Gentle facial cleanser for all skin types',
  },
  {
    productId: 'sku_10008',
    sku: 'CLINIQUE-MOISTURIZER-001',
    name: 'Clinique Dramatically Different Moisturizing Lotion',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'clinique',
    price: 48000,
    description: 'Lightweight moisturizer with hydrating formula',
  },
  {
    productId: 'sku_10009',
    sku: 'SHISEIDO-SERUM-001',
    name: 'Shiseido Ultimune Power Infusing Serum',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'shiseido',
    price: 65000,
    description: 'Advanced serum with immune-boosting technology',
  },
  {
    productId: 'sku_10010',
    sku: 'SHISEIDO-CREAM-001',
    name: 'Shiseido Future Solution LX Cream',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'shiseido',
    price: 85000,
    description: 'Luxury anti-aging cream',
  },
  {
    productId: 'sku_10011',
    sku: 'ESTEE-LAUDER-PERFUME-001',
    name: 'Estee Lauder Beautiful Eau de Parfum',
    categoryId: 'cat_04',
    category: 'Fragrance',
    brand: 'estee_lauder',
    price: 95000,
    description: 'Classic floral fragrance',
  },
  {
    productId: 'sku_10012',
    sku: 'MAC-LIPSTICK-001',
    name: 'MAC Ruby Lipstick',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'mac',
    price: 32000,
    description: 'Iconic ruby red lipstick',
  },
  {
    productId: 'sku_10013',
    sku: 'LANCOME-MASCARA-001',
    name: 'Lancome Hypnose Drama Mascara',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'lancome',
    price: 42000,
    description: 'Dramatic volumizing mascara',
  },
  {
    productId: 'sku_10014',
    sku: 'LANCOME-SERUM-001',
    name: 'Lancome Advanced Genifique Serum',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'lancome',
    price: 72000,
    description: 'Youth-activating serum',
  },
  {
    productId: 'sku_10015',
    sku: 'DIOR-FOUNDATION-001',
    name: 'Dior Forever Foundation',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'dior',
    price: 58000,
    description: 'Long-wearing foundation with natural finish',
  },
  {
    productId: 'sku_10016',
    sku: 'DIOR-LIPSTICK-001',
    name: 'Dior Rouge Lipstick',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'dior',
    price: 48000,
    description: 'Luxurious lipstick with satin finish',
  },
  {
    productId: 'sku_10017',
    sku: 'CHANEL-PERFUME-001',
    name: 'Chanel No. 5 Eau de Parfum',
    categoryId: 'cat_04',
    category: 'Fragrance',
    brand: 'chanel',
    price: 125000,
    description: 'Iconic fragrance',
  },
  {
    productId: 'sku_10018',
    sku: 'CHANEL-LIPSTICK-001',
    name: 'Chanel Rouge Coco Lipstick',
    categoryId: 'cat_02',
    category: 'Makeup',
    brand: 'chanel',
    price: 55000,
    description: 'Legendary lipstick',
  },
  {
    productId: 'sku_10019',
    sku: 'OLAY-MOISTURIZER-001',
    name: 'Olay Regenerist Micro-Sculpting Cream',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'olay',
    price: 32000,
    description: 'Anti-aging moisturizer',
  },
  {
    productId: 'sku_10020',
    sku: 'OLAY-SERUM-001',
    name: 'Olay Regenerist Retinol24 Serum',
    categoryId: 'cat_01',
    category: 'Face Care',
    brand: 'olay',
    price: 28000,
    description: 'Retinol-based anti-aging serum',
  },
];

export const CATEGORIES = [
  { id: 'cat_01', name: 'Face Care' },
  { id: 'cat_02', name: 'Makeup' },
  { id: 'cat_03', name: 'Sun Care' },
  { id: 'cat_04', name: 'Fragrance' },
];

export const BRANDS = [
  'adidas',
  'loreal',
  'maybelline',
  'neutrogena',
  'clinique',
  'shiseido',
  'estee_lauder',
  'mac',
  'lancome',
  'dior',
  'chanel',
  'olay',
];

export function getProductById(productId: string): Product | undefined {
  return SAMPLE_PRODUCTS.find(p => p.productId === productId);
}

export function getProductsByCategory(categoryId: string): Product[] {
  return SAMPLE_PRODUCTS.filter(p => p.categoryId === categoryId);
}

export function getProductsByBrand(brand: string): Product[] {
  return SAMPLE_PRODUCTS.filter(p => p.brand === brand);
}

export function searchProducts(query: string): Product[] {
  const lowerQuery = query.toLowerCase();
  return SAMPLE_PRODUCTS.filter(
    p =>
      p.name.toLowerCase().includes(lowerQuery) ||
      p.brand.toLowerCase().includes(lowerQuery) ||
      p.category.toLowerCase().includes(lowerQuery)
  );
}

export function getCategoryName(categoryId: string): string {
  return CATEGORIES.find(c => c.id === categoryId)?.name || 'Unknown';
}
