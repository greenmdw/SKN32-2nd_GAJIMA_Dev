import { useState, useEffect } from 'react';
import { useLocation, useParams } from 'wouter';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { SAMPLE_PRODUCTS, getProductById } from '@/lib/productData';
import { logViewEvent, logCartEvent } from '@/lib/eventLogger';
import { useCart } from '@/contexts/CartContext';
import { ArrowLeft, ShoppingCart, Plus, Minus } from 'lucide-react';
import { toast } from 'sonner';
import RecommendedProducts from '@/components/RecommendedProducts';

export default function ProductDetail() {
  const [, setLocation] = useLocation();
  const params = useParams();
  const productId = params?.id;
  const product = productId ? getProductById(productId) : null;
  const { addItem } = useCart();
  const [quantity, setQuantity] = useState(1);

  // Log view event on mount
  useEffect(() => {
    if (product) {
      logViewEvent(
        product.productId,
        product.categoryId,
        product.brand,
        product.price,
        `/product/${product.productId}`,
        '/products'
      );
    }
  }, [product]);

  if (!product) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-400 text-lg mb-4">Product not found</p>
          <Button onClick={() => setLocation('/products')}>Back to Products</Button>
        </div>
      </div>
    );
  }

  const handleAddToCart = async () => {
    addItem(product, quantity);
    
    // Log cart event
    await logCartEvent(
      product.productId,
      product.categoryId,
      product.brand,
      product.price,
      quantity,
      `/product/${product.productId}`,
      '/products'
    );

    toast.success(`Added ${quantity} item(s) to cart`);
    setQuantity(1);
  };



  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <Button
            variant="ghost"
            className="text-slate-400 hover:text-slate-100"
            onClick={() => setLocation('/products')}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Products
          </Button>
        </div>
      </div>

      {/* Product Detail */}
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mb-16">
          {/* Product Image */}
          <div className="flex items-center justify-center">
            <Card className="w-full aspect-square bg-gradient-to-br from-slate-700 to-slate-900 border-slate-700 flex items-center justify-center">
              <div className="text-center">
                <div className="text-8xl mb-4">💄</div>
                <p className="text-slate-500">{product.sku}</p>
              </div>
            </Card>
          </div>

          {/* Product Info */}
          <div className="flex flex-col justify-center">
            <div className="mb-6">
              <p className="text-sm text-slate-500 mb-2">{product.category}</p>
              <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 mb-2">
                {product.name}
              </h1>
              <p className="text-lg text-slate-400">{product.brand.toUpperCase()}</p>
            </div>

            {/* Price */}
            <div className="mb-8">
              <p className="text-slate-500 text-sm mb-2">Price</p>
              <p className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
                ₩{product.price.toLocaleString()}
              </p>
            </div>

            {/* Description */}
            {product.description && (
              <div className="mb-8">
                <p className="text-slate-400">{product.description}</p>
              </div>
            )}

            {/* Quantity Selector */}
            <div className="mb-8">
              <p className="text-slate-400 text-sm mb-3">Quantity</p>
              <div className="flex items-center gap-4">
                <Button
                  size="sm"
                  variant="outline"
                  className="border-slate-700 text-slate-400 hover:text-slate-100"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                >
                  <Minus className="w-4 h-4" />
                </Button>
                <Input
                  type="number"
                  min="1"
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 bg-slate-800 border-slate-700 text-center text-slate-100"
                />
                <Button
                  size="sm"
                  variant="outline"
                  className="border-slate-700 text-slate-400 hover:text-slate-100"
                  onClick={() => setQuantity(quantity + 1)}
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Add to Cart Button */}
            <Button
              size="lg"
              className="w-full bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white mb-4"
              onClick={handleAddToCart}
            >
              <ShoppingCart className="w-5 h-5 mr-2" />
              Add to Cart
            </Button>

            <Button
              size="lg"
              variant="outline"
              className="w-full border-slate-700 text-slate-400 hover:text-slate-100"
              onClick={() => setLocation('/products')}
            >
              Continue Shopping
            </Button>
          </div>
        </div>

        {/* Recommended Products */}
        <RecommendedProducts
          productId={product.productId}
          categoryId={product.categoryId}
          brand={product.brand}
          onProductSelect={(id) => setLocation(`/product/${id}`)}
        />
      </div>
    </div>
  );
}
