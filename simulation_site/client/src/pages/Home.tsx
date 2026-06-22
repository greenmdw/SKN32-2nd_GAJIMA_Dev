import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { Zap, ShoppingBag, TrendingUp } from "lucide-react";

export default function Home() {
  const [, setLocation] = useLocation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Navigation */}
        <nav className="border-b border-slate-700/50 backdrop-blur-sm sticky top-0 z-40">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400">
              Churn Simulator
            </h1>
            <Button
              className="bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white"
              onClick={() => setLocation("/products")}
            >
              <ShoppingBag className="w-4 h-4 mr-2" />
              Shop Now
            </Button>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="container mx-auto px-4 py-24">
          <div className="max-w-4xl mx-auto text-center mb-16">
            <h2 className="text-6xl md:text-7xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 leading-tight">
              Real-time E-Commerce Churn Simulation
            </h2>
            <p className="text-xl text-slate-300 mb-8 leading-relaxed">
              Experience a live cosmetics shopping simulation with real-time churn prediction. 
              Watch as your shopping behavior is analyzed and your churn probability is calculated in real-time.
            </p>
            <Button
              size="lg"
              className="bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white text-lg px-8 py-6"
              onClick={() => setLocation("/products")}
            >
              <Zap className="w-5 h-5 mr-2" />
              Start Simulation
            </Button>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-20">
            {/* Feature 1 */}
            <div className="group bg-slate-800/50 backdrop-blur border border-slate-700 rounded-lg p-8 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10">
              <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <ShoppingBag className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-slate-100 mb-3">Browse Products</h3>
              <p className="text-slate-400">
                Explore a curated selection of premium cosmetics from top brands. Filter by category and brand to find exactly what you're looking for.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group bg-slate-800/50 backdrop-blur border border-slate-700 rounded-lg p-8 hover:border-purple-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/10">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-slate-100 mb-3">Real-time Analytics</h3>
              <p className="text-slate-400">
                See your churn probability updated in real-time as you browse, add items to cart, and make purchases.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group bg-slate-800/50 backdrop-blur border border-slate-700 rounded-lg p-8 hover:border-pink-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-pink-500/10">
              <div className="w-12 h-12 bg-gradient-to-br from-pink-500 to-red-500 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-slate-100 mb-3">Smart Recommendations</h3>
              <p className="text-slate-400">
                Get personalized product recommendations based on your browsing behavior and preferences.
              </p>
            </div>
          </div>

          {/* How It Works */}
          <div className="mt-24 bg-gradient-to-r from-slate-800/50 to-slate-700/50 backdrop-blur border border-slate-700 rounded-lg p-12">
            <h3 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400 mb-8 text-center">
              How It Works
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {[
                { num: "1", title: "Browse", desc: "Explore cosmetics catalog" },
                { num: "2", title: "Add", desc: "Add items to your cart" },
                { num: "3", title: "Analyze", desc: "Real-time churn prediction" },
                { num: "4", title: "Purchase", desc: "Complete your order" },
              ].map((step, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-lg">
                    {step.num}
                  </div>
                  <h4 className="font-bold text-slate-100 mb-2">{step.title}</h4>
                  <p className="text-sm text-slate-400">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* CTA Section */}
          <div className="mt-20 text-center">
            <p className="text-slate-400 mb-6">Ready to experience the simulation?</p>
            <Button
              size="lg"
              className="bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white text-lg px-8 py-6"
              onClick={() => setLocation("/products")}
            >
              <ShoppingBag className="w-5 h-5 mr-2" />
              Enter the Simulation
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
